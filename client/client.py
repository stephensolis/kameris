from __future__ import absolute_import, division, unicode_literals

import base64
import boto3
import collections
import copy
import itertools
import json
import logging
import os
from ruamel.yaml import YAML
from six import iteritems
from six.moves import range
import sys
import time
import watchtower

from . import classify
from . import mds
from . import selection
from . import utils


def make_aws_args(settings):
    return {
        'aws_access_key_id': settings['aws_key'],
        'aws_secret_access_key': settings['aws_secret'],
        'region_name': settings['region']
    }


def experiment_paths(local_dirs, job_name, exp_name):
    output_dir = os.path.join(local_dirs['output'], job_name, exp_name)

    return {
        'client_dir': os.path.dirname(os.path.realpath(__file__)),
        'archives_dir': local_dirs['archives'],
        'metadata_dir': local_dirs['metadata'],
        'output_dir': output_dir,
        'fasta_dir': os.path.join(output_dir, 'fasta'),
        'metadata_file': os.path.join(output_dir, 'metadata.json'),
        'log_file': os.path.join(output_dir, 'log.txt')
    }


def preprocess_experiments(experiments):
    def inflate_option_vals(option_vals):
        if isinstance(option_vals, str):
            [start, end] = option_vals.split('..')
            return range(int(start), int(end)+1)
        else:
            return option_vals

    def exp_name_with_options(exp_name, option_values):
        return exp_name + '-' + '-'.join('{}{}'.format(option_key, option_val)
                                         for (option_key, option_val)
                                         in iteritems(dict(option_values)))

    final_experiments = collections.OrderedDict()
    for exp_name, exp_options in iteritems(experiments):
        if 'expand_options' in exp_options:
            expand_options = exp_options['expand_options']
            expand_option_values = itertools.product(*(
                ((option_key, option_val)
                 for option_val in inflate_option_vals(option_vals))
                for (option_key, option_vals) in iteritems(expand_options)
            ))

            for i, exp_option_values in enumerate(expand_option_values):
                new_exp_name = exp_name_with_options(exp_name,
                                                     exp_option_values)
                new_exp_options = dict(exp_option_values, **exp_options)
                if i == 0:
                    first_new_exp_name = new_exp_name
                elif ('no_copy' not in expand_options or
                        not expand_options['no_copy']):
                    new_exp_options['copy'] = {
                        'from': first_new_exp_name,
                        'files': ['fasta', 'metadata.json'],
                        'skip': ['select', 'retrieve']
                    }
                final_experiments[new_exp_name] = new_exp_options
        else:
            final_experiments[exp_name] = exp_options

    return final_experiments


def preprocess_steps(steps, paths, exp_options):
    string_substitutions = dict(exp_options, **paths)

    def perform_on_options_keys(func, options, keys):
        for key in keys:
            if key in options:
                if isinstance(options[key], list):
                    options[key] = [func(x) for x in options[key]]
                else:
                    options[key] = func(options[key])

    def do_option_substitutions(options, keys):
        perform_on_options_keys(lambda s: s.format(**string_substitutions),
                                options, keys)

    def make_output_paths(options, keys):
        do_option_substitutions(options, keys)
        perform_on_options_keys(lambda p: (p if os.path.isabs(p)
                                           else os.path.join(
                                               paths['output_dir'], p
                                           )),
                                options, keys)

    steps = copy.deepcopy(steps)
    for step_options in steps:
        if step_options['type'] == 'select':
            do_option_substitutions(step_options, [
                'pick_group', 'postprocess'
            ])
            step_options['archives_dir'] = paths['archives_dir']
            step_options['metadata_dir'] = paths['metadata_dir']
            step_options['fasta_output_dir'] = paths['fasta_dir']
            step_options['metadata_output_file'] = paths['metadata_file']
        elif step_options['type'] == 'command':
            do_option_substitutions(step_options, ['command'])
            make_output_paths(step_options, ['save_files'])
        elif step_options['type'] == 'mds':
            make_output_paths(step_options, ['dists_file', 'output_file'])
        elif step_options['type'] == 'classify':
            step_options['metadata_file'] = paths['metadata_file']
            make_output_paths(step_options, ['features_file', 'output_file'])
        elif step_options['type'] == 'plots':
            step_options['plots_script'] = os.path.join(paths['client_dir'],
                                                        'make_plots.wls')
            step_options['metadata_file'] = paths['metadata_file']
            make_output_paths(step_options, [
                'mds_file', 'classification_file', 'output_file'
            ])

    return steps


def run_experiment_copy(copy_options, paths, local_dirs, job_name):
    with utils.log_step("copying files from experiment '{}'"
                        .format(copy_options['from']), start_stars=True):
        for j, filename in enumerate(copy_options['files']):
            with utils.log_step("file '{}' ({}/{})".format(
                    filename, j+1, len(copy_options['files']))):
                if ('real_copy' not in copy_options or
                        not copy_options['real_copy']):
                    copy_func = utils.symlink
                else:
                    copy_func = utils.cp_r

                src_paths = experiment_paths(local_dirs, job_name,
                                             copy_options['from'])
                copy_func(
                    os.path.join(src_paths['output_dir'], filename),
                    os.path.join(paths['output_dir'], filename)
                )


def run_experiment_steps(steps, exp_options):
    log = logging.getLogger('modmap')

    for i, step_options in enumerate(steps):
        step_desc = "step '{}' ({}/{})".format(step_options['type'], i+1,
                                               len(steps))

        if 'copy' in exp_options and (i in exp_options['copy']['skip'] or
                                      step_options['type'] in
                                      exp_options['copy']['skip']):
            log.info("*** skipping {} because of 'copy' directive"
                     .format(step_desc))
            continue

        with utils.log_step(step_desc, start_stars=True):
            if step_options['type'] == 'select':
                selection.run_selection(step_options, exp_options)
            elif step_options['type'] == 'command':
                utils.run_command_logged(step_options['command'], shell=True)
            elif step_options['type'] == 'mds':
                mds.run_mds(step_options)
            elif step_options['type'] == 'classify':
                classify.run_experiment(step_options)
            elif step_options['type'] == 'plots':
                utils.run_command_logged([
                    'wolframscript', step_options['plots_script'],
                    base64.b64encode(json.dumps(step_options))
                ])


def setup_logging(job_name, settings):
    log = logging.getLogger('modmap')
    log.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')

    console_logger = logging.StreamHandler(stream=sys.stdout)
    console_logger.setFormatter(formatter)
    log.addHandler(console_logger)

    if 'remote_logging' in settings:
        remote_log_settings = settings['remote_logging']
        aws_session = boto3.session.Session(**make_aws_args(settings))
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


def run_job(jobdesc_filename, settings_filename):
    # load config files
    with open(jobdesc_filename, 'r') as infile:
        job_options = YAML(typ='safe').load(infile)
    with open(settings_filename, 'r') as infile:
        settings = YAML(typ='safe').load(infile)

    local_dirs = settings['local_dirs']
    job_name = job_options['name']
    experiments = preprocess_experiments(job_options['experiments'])

    log, formatter = setup_logging(job_name, settings)

    for i, (exp_name, exp_options) in enumerate(iteritems(experiments)):
        with utils.log_step("experiment '{}' ({}/{})"
                            .format(exp_name, i+1, len(experiments)),
                            start_stars=True):
            exp_options['experiment_name'] = exp_name

            # get ready
            paths = experiment_paths(local_dirs, job_name, exp_name)
            steps = preprocess_steps(job_options['steps'], paths, exp_options)
            utils.mkdir_p(paths['output_dir'])

            # start file log
            file_logger = logging.FileHandler(paths['log_file'], mode='w')
            file_logger.setFormatter(formatter)
            log.addHandler(file_logger)

            # copy files if requested
            if 'copy' in exp_options:
                run_experiment_copy(exp_options['copy'], paths, local_dirs,
                                    job_name)

            # run steps
            run_experiment_steps(steps, exp_options)

            # finish file log
            file_logger.close()
            log.removeHandler(file_logger)
