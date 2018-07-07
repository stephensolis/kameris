from __future__ import absolute_import, division, unicode_literals

import logging
import subprocess


def run_command_logged(command, **kwargs):
    log = logging.getLogger('kameris')
    log.info('running command "%s"', command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True, **kwargs)
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line:
            log.info('%s', line.strip())
    if process.wait() != 0:
        raise subprocess.CalledProcessError(process.returncode, command, None)


def run_command_step(options, exp_options):
    run_command_logged(options['command'], shell=True)
