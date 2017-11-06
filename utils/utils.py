from __future__ import absolute_import, division, unicode_literals


import contextlib
import logging
import os
import re
import timeit
import shutil
import subprocess


# 'multiline lambda' runner

lambda_str_cache = {}
def call_string_extended_lambda(func_str, *args, **kwargs): # NOQA (cache line above)
    if func_str not in lambda_str_cache:
        context = {}
        exec(re.sub('^lambda(.*):', 'def func(\\1):', func_str), context)
        lambda_str_cache[func_str] = context['func']

    return lambda_str_cache[func_str](*args, **kwargs)


# filesystem-related

def mkdir_p(dir):
    try:
        os.makedirs(dir)
    except OSError:
        pass


def symlink(src, dest):
    if os.name == 'nt':
        if os.path.isdir(src):
            subprocess.check_output('mklink /j "{}" "{}"'.format(dest, src),
                                    shell=True)
        else:
            subprocess.check_output('mklink /h "{}" "{}"'.format(dest, src),
                                    shell=True)
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
