from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from backports import tempfile
import json
import kameris_formats
import os
import sklearn
from sklearn.externals import joblib
from tabulate import tabulate

from ..job_steps import backend
from ..utils import download_utils, job_utils


def run(args):
    # setup logging
    log, _ = job_utils.setup_logging('', {})

    # open the model file
    if os.path.exists(args.model):
        model_file = open(args.model, 'rb')
    else:
        if download_utils.is_url(args.model):
            model_url = args.model
        else:
            model_url = download_utils.url_for_file(args.model + '.mm-model',
                                                    args.urls_file, 'models')
        model_file = download_utils.open_url_cached(model_url, 'rb',
                                                    args.force_download)

    # load the model
    with job_utils.log_step('loading model'):
        model_data = joblib.load(model_file)
        if model_data['sklearn_version'] != sklearn.__version__:
            log.warning('the version of scikit-learn installed now is '
                        'different from the one used during training '
                        '(%s vs %s), you may experience issues',
                        model_data['sklearn_version'], sklearn.__version__)

    # compute CGRs for inputs
    with job_utils.log_step('computing input CGRs'):
        with tempfile.TemporaryDirectory() as temp_dir:
            cgrs_file = os.path.join(temp_dir, 'cgrs.mm-repr')
            options = dict(model_data['generation_options'],
                           fasta_output_dir=args.files, output_file=cgrs_file,
                           disable_avx=args.disable_avx)
            backend.run_backend_kmers(options, {})

            cgrs = []
            reader = kameris_formats.repr_reader(cgrs_file)
            for i in range(reader.count):
                cgrs.append(reader.read_matrix(i, flatten=True))
            reader.file.close()

    # get list of input files
    filenames = sorted(f for f in os.listdir(args.files) if
                       os.path.isfile(os.path.join(args.files, f)))

    # run predictions
    with job_utils.log_step('running predictions'):
        predictor = model_data['predictor']
        if hasattr(predictor, 'predict_proba'):
            results = predictor.predict_proba(cgrs)
        else:
            results = predictor.predict(cgrs)

    # build and write results
    if hasattr(predictor, 'predict_proba'):
        results = dict(zip(filenames, [
            sorted(zip(predictor.classes_, result), reverse=True,
                   key=lambda r: r[1])
            for result in results
        ]))
    else:
        results = dict(zip(filenames, results))
    with open('results.json', 'w') as file:
        json.dump(results, file)
    log.info('wrote results to results.json')

    # print results
    print()
    print('Top-1 prediction summary:')
    print(tabulate(zip(
        filenames, [
            '{} ({:.1%})'.format(*results[f][0])
            if isinstance(results[f], list) else results[f]
            for f in filenames
        ]
    )))
