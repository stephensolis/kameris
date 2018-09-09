from backports import tempfile
import dotmap
import json
import os
import zipfile

from kameris.subcommands import classify, run_job, summarize

from .helpers import chdir


def check_classify_model(model, tempdir, check_results=True):
    with tempfile.TemporaryDirectory() as genomes_dir:
        # fetch and extract genomes
        archive_filename = os.path.join('demo', 'hiv1-genomes.zip')
        with zipfile.ZipFile(archive_filename, 'r') as archive:
            archive.extractall(genomes_dir)

        # run classification
        with chdir(tempdir):
            args = dotmap.DotMap({
                'model': model,
                'files': genomes_dir,
                'disable_avx': True
            })
            classify.run(args)

            # check results
            with open('results.json', 'r') as f:
                results = json.load(f)
            if check_results:
                assert results == {
                    'A1.fasta': 'A1',
                    'A6.fasta': 'A6',
                    'B.fasta': 'B',
                    'C.fasta': 'C',
                }


def test_classify_existing_model(shared_tempdir):
    check_classify_model('hiv1-linearsvm', shared_tempdir)


def test_train_model(shared_tempdir):
    root_dir = os.getcwd()
    with chdir(shared_tempdir):
        args = dotmap.DotMap({
            'job_file': os.path.join(root_dir, 'tests', 'fixtures',
                                     'hiv1-lanl-small.yml'),
            'settings_file': os.path.join(root_dir, 'demo', 'settings.yml'),
            'disable_avx': True
        })
        run_job.run(args)


def test_summarize(shared_tempdir):
    with chdir(shared_tempdir):
        args = dotmap.DotMap({
            'job_dir': os.path.join('output', 'hiv1-lanl-whole'),
            'top_n': 1
        })
        summarize.run(args)


def test_classify_new_model(shared_tempdir):
    model_base_filename = os.path.join(
        shared_tempdir, 'output', 'hiv1-lanl-whole', 'subtype-k=4',
        'classification-kmers_'
    )
    check_classify_model(
        model_base_filename + 'linear-svm.mm-model', shared_tempdir
    )
    check_classify_model(
        model_base_filename + 'multilayer-perceptron.mm-model', shared_tempdir,
        check_results=False
    )
