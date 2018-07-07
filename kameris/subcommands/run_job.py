from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import boto3
import collections
import copy
import itertools
import logging
import os
import random
from ruamel.yaml import YAML
import six
from six import iteritems
from six.moves import range
import sys
import time
import watchtower

from ..job_steps import step_runners
from ..utils import fs_utils, job_utils


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
        'fasta_output_dir': os.path.join(output_dir, 'fasta'),
        'metadata_output_file': os.path.join(output_dir, 'metadata.json'),
        'log_file': os.path.join(output_dir, 'log.txt'),
        'experiment_rerun_file': os.path.join(output_dir,
                                              'rerun_experiment.yml')
    }


def preprocess_experiments(experiments):
    def inflate_option_vals(option_vals):
        if isinstance(option_vals, six.string_types):
            [start, end] = option_vals.split('..')
            return range(int(start), int(end)+1)
        else:
            return option_vals

    def exp_name_with_options(exp_name, option_values):
        return exp_name + '-' + '-'.join('{}={}'.format(option_key, option_val)
                                         for (option_key, option_val)
                                         in iteritems(dict(option_values)))

    # handle expand_options
    final_experiments = collections.OrderedDict()
    for exp_name, exp_options in iteritems(experiments):
        if 'expand_options' in exp_options:
            clean_exp_options = exp_options.copy()
            clean_exp_options.pop('expand_options')

            expand_options = exp_options['expand_options']
            expand_option_values = itertools.product(*(
                [(option_key, option_val)
                 for option_val in inflate_option_vals(option_vals)]
                for (option_key, option_vals) in iteritems(expand_options)
                if option_key != 'no_copy'
            ))

            for i, exp_option_values in enumerate(expand_option_values):
                new_exp_name = exp_name_with_options(exp_name,
                                                     exp_option_values)
                new_exp_options = dict(exp_option_values, **clean_exp_options)
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
            step_options['fasta_output_dir'] = paths['fasta_output_dir']
            step_options['metadata_output_file'] = \
                paths['metadata_output_file']
        elif step_options['type'] == 'command':
            do_option_substitutions(step_options, ['command'])
        elif step_options['type'] == 'kmers':
            step_options['fasta_output_dir'] = paths['fasta_output_dir']
            make_output_paths(step_options, ['output_file'])
            do_option_substitutions(step_options, ['k'])
        elif step_options['type'] == 'distances':
            make_output_paths(step_options, ['input_file', 'output_prefix'])
        elif step_options['type'] == 'mds':
            make_output_paths(step_options, ['dists_file', 'output_file'])
        elif step_options['type'] == 'classify':
            step_options['metadata_file'] = paths['metadata_output_file']
            make_output_paths(step_options, ['features_file', 'output_file'])

    return steps


def run_experiment_copy(copy_options, paths, local_dirs, job_name):
    with job_utils.log_step("copying files from experiment '{}'"
                            .format(copy_options['from']), start_stars=True):
        for j, filename in enumerate(copy_options['files']):
            with job_utils.log_step("file '{}' ({}/{})".format(
                    filename, j+1, len(copy_options['files']))):
                if ('real_copy' not in copy_options or
                        not copy_options['real_copy']):
                    copy_func = fs_utils.symlink
                else:
                    copy_func = fs_utils.cp_r

                src_paths = experiment_paths(local_dirs, job_name,
                                             copy_options['from'])
                copy_func(
                    os.path.join(src_paths['output_dir'], filename),
                    os.path.join(paths['output_dir'], filename)
                )


def run_experiment_steps(steps, exp_options):
    log = logging.getLogger('kameris')

    for i, step_options in enumerate(steps):
        step_desc = "step '{}' ({}/{})".format(step_options['type'], i+1,
                                               len(steps))

        if 'copy' in exp_options and (i in exp_options['copy']['skip'] or
                                      step_options['type'] in
                                      exp_options['copy']['skip']):
            log.info("*** skipping %s because of 'copy' directive", step_desc)
            continue

        with job_utils.log_step(step_desc, start_stars=True):
            step_runners[step_options['type']](step_options, exp_options)


def setup_logging(job_name, settings):
    log = logging.getLogger('kameris')
    log.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s %(message)s')

    console_logger = logging.StreamHandler(stream=sys.stdout)
    console_logger.setFormatter(formatter)
    log.addHandler(console_logger)

    if 'remote_logging' in settings:
        remote_log_settings = settings['remote_logging']
        aws_session = boto3.session.Session(
            **make_aws_args(remote_log_settings)
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


def run(args):
    job_options = YAML(typ='safe').load(args.job_file)

    settings = {}
    for settings_file in args.settings_files:
        settings.update(YAML(typ='safe').load(settings_file))

    local_dirs = settings['local_dirs']
    job_name = job_options['name']

    experiments = job_options['experiments']
    if isinstance(experiments, six.string_types):
        experiments = job_utils.call_string_extended_lambda(
            experiments.format(**experiment_paths(local_dirs, job_name, ''))
        )
    experiments = preprocess_experiments(experiments)

    log, formatter = setup_logging(job_name, settings)

    for i, (exp_name, exp_options) in enumerate(iteritems(experiments)):
        with job_utils.log_step("experiment '{}' ({}/{})"
                                .format(exp_name, i+1, len(experiments)),
                                start_stars=True):
            exp_options = exp_options.copy()
            exp_options['experiment_name'] = exp_name

            # get ready
            paths = experiment_paths(local_dirs, job_name, exp_name)
            steps = preprocess_steps(job_options['steps'], paths, exp_options)
            if isinstance(exp_options['groups'], six.string_types):
                exp_options['groups'] = job_utils.call_string_extended_lambda(
                    exp_options['groups'].format(**dict(exp_options, **paths))
                )
            fs_utils.mkdir_p(paths['output_dir'])

            # start file log
            file_logger = logging.FileHandler(paths['log_file'], mode='w')
            file_logger.setFormatter(formatter)
            log.addHandler(file_logger)

            # seed the RNG
            if 'random_seed' in job_options:
                random_seed = job_options['random_seed']
            else:
                random_seed = random.getrandbits(32)
            log.info('using random seed value %d', random_seed)
            random.seed(random_seed)

            # create a re-run file
            with open(paths['experiment_rerun_file'], 'w') as rerun_file:
                YAML().dump({
                    'name': job_name,
                    'random_seed': random_seed,
                    'experiments': {
                        exp_name: exp_options
                    },
                    'steps': job_options['steps']
                }, rerun_file)

            # copy files if requested
            if 'copy' in exp_options:
                run_experiment_copy(exp_options['copy'], paths, local_dirs,
                                    job_name)

            # run steps
            run_experiment_steps(steps, exp_options)

            # finish file log
            file_logger.close()
            log.removeHandler(file_logger)
