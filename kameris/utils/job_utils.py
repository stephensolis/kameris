from __future__ import absolute_import, division, unicode_literals


import contextlib
import logging
import re
import timeit


# 'multiline lambda' runner

lambda_str_cache = {}
def call_string_extended_lambda(func_str, *args, **kwargs):  # NOQA (cache line above)
    if func_str not in lambda_str_cache:
        context = {}
        exec(re.sub('^lambda(.*):', 'def func(\\1):', func_str), context)
        lambda_str_cache[func_str] = context['func']

    return lambda_str_cache[func_str](*args, **kwargs)


# for formatted log output

class LoggerAsFile:
    def __init__(self, logger_name):
        self.log = logging.getLogger(logger_name)

    def write(self, string):
        string = string.strip()
        if string:
            self.log.info('%s', string)

    def flush(self):
        pass


@contextlib.contextmanager
def log_step(step_text, start_stars=False):
    log = logging.getLogger('kameris')
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
