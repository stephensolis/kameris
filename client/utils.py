from __future__ import absolute_import, division, unicode_literals


import contextlib
import logging
import os
import timeit
import shutil
import subprocess


# filesystem-related

def mkdir_p(dir):
    try:
        os.makedirs(dir)
    except OSError:
        pass


def symlink(src, dest):
    if os.name == 'nt':
        if os.path.isdir(src):
            subprocess.check_output(['mklink', '/d', dest, src], shell=True)
        else:
            subprocess.check_output(['mklink', dest, src], shell=True)
    else:
        os.symlink(src, dest)


def cp_r(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest)
    else:
        shutil.copy(src, dest)


# for formatted log output

class LoggerFileAdapter:
    def __init__(self, logger_name):
        self.log = logging.getLogger(logger_name)

    def write(self, str):
        str = str.strip()
        if str:
            self.log.info('%s', str)

    def flush(self):
        pass


@contextlib.contextmanager
def log_step(step_text, start_stars=False):
    log = logging.getLogger('modmap')
    if start_stars:
        step_format = '*** %s %s'
    else:
        step_format = '%s %s'

    log.info(step_format, 'started', step_text)
    start_time = timeit.default_timer()
    yield
    end_time = timeit.default_timer()
    log.info(step_format + ' in %.2f seconds',
             'finished', step_text, end_time - start_time)


def run_command_logged(command, **kwargs):
    log = logging.getLogger('modmap')
    log.info('running command "%s"', command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True, **kwargs)
    for line in iter(process.stdout.readline, ""):
        line = line.strip()
        if line:
            log.info('%s', line)
