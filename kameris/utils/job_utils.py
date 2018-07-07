from __future__ import absolute_import, division, unicode_literals


import boto3
import contextlib
import logging
import re
import sys
import time
import timeit
import watchtower


# 'multiline lambda' support

def parse_multiline_lambda_str(func_str, **context):
    exec(re.sub('^lambda(.*):', 'def func(\\1):', func_str), context)
    return context['func']


# for formatted log output

def _make_aws_args(settings):
    return {
        'aws_access_key_id': settings['aws_key'],
        'aws_secret_access_key': settings['aws_secret'],
        'region_name': settings['region']
    }


def setup_logging(job_name, settings):
    log = logging.getLogger('kameris')
    log.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')

    console_logger = logging.StreamHandler(stream=sys.stdout)
    console_logger.setFormatter(formatter)
    log.addHandler(console_logger)

    if 'remote_logging' in settings:
        remote_log_settings = settings['remote_logging']
        if remote_log_settings['destination'] != 'cloudwatch':
            log.warning('*** unknown log destination %s, skipping',
                        remote_log_settings['destination'])
        return log, formatter

        aws_session = boto3.session.Session(
            **_make_aws_args(remote_log_settings)
        )
        log_stream_name = '{}-{}'.format(job_name, int(time.time()))

        log.info('*** logging to AWS CloudFront stream %s', log_stream_name)
        aws_logger = watchtower.CloudWatchLogHandler(
            log_group=remote_log_settings['log_group'],
            stream_name=log_stream_name,
            boto3_session=aws_session,
            send_interval=5
        )
        aws_logger.setFormatter(formatter)
        log.addHandler(aws_logger)

    return log, formatter


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
