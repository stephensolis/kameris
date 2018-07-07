from __future__ import absolute_import, division, unicode_literals

import appdirs
import hashlib
import json
import logging
import os
import requests
from ruamel.yaml import YAML
from six.moves import urllib
import sys
from tqdm import tqdm

from . import defaults, fs_utils, job_utils


def is_url(url):
    return urllib.parse.urlparse(url).scheme in {'http', 'https'}


def _google_download_url(url):
    data = json.loads(
        requests.post(url, headers={'x-drive-first-party': 'DriveWebUi'})
                .text.splitlines()[1]
    )
    return (data['downloadUrl'], data['sizeBytes'])


def download_file(url, dest):
    log = logging.getLogger('kameris')
    with job_utils.log_step("downloading '{}'".format(url)):
        size = None
        if urllib.parse.urlparse(url).netloc == 'drive.google.com':
            log.info('preparing download (this may take a while)')
            url, size = _google_download_url(url)

        with requests.get(url, stream=True) as r:
            if not size:
                size = int(r.headers['content-length'])
            with open(dest, 'wb') as f:
                with tqdm(total=size, unit='b', unit_scale=True,
                          file=job_utils.LoggerAsFile('kameris')) as pbar:
                    for chunk in r.iter_content(chunk_size=1048576):
                        f.write(chunk)
                        pbar.update(len(chunk))


urls = None
def url_for_file(path, urls_file, filetype):  # NOQA (cache line above)
    global urls
    if not urls:
        urls = YAML(typ='safe').load(read_file_or_url(
            urls_file or defaults.locations['urls_file']
        ))

    filename = os.path.splitext(os.path.basename(path))[0]
    if filetype == 'models':
        python_ver = 'python{}'.format(sys.version_info.major)
        return urls[filetype][filename][python_ver]
    else:
        return urls[filetype][filename]


def open_url_cached(url, mode, force_download=False):
    log = logging.getLogger('kameris')

    cache_dir = os.path.join(appdirs.user_data_dir('Kameris', 'Kameris'),
                             'cache')
    fs_utils.mkdir_p(cache_dir)

    cache_key = hashlib.md5(url.encode('utf-8')).hexdigest()
    cache_filename = os.path.join(cache_dir, cache_key)
    if not force_download and os.path.exists(cache_filename):
        log.info("file '%s' already downloaded, using cached version", url)
        return open(cache_filename, mode)
    else:
        download_file(url, cache_filename)
        return open(cache_filename, mode)


def read_file_or_url(path):
    if is_url(path):
        log = logging.getLogger('kameris')
        message = "retrieving '{}'".format(path)
        if log.handlers:
            log.info(message)
        else:
            print('INFO     ' + message)
        return requests.get(path).text
    else:
        with open(path, 'r') as f:
            return f.read()
