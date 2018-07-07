from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os

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
                                                    args.urls_file, 'model')
        model_file = download_utils.open_url_cached(model_url, 'rb',
                                                    args.force_download)

    # load the model
    model_file.read()
