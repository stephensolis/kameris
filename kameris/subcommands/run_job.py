from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import boto3
import collections
import copy
import functools
import itertools
import json
import jsonschema
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


def preprocess_experiments(experiments, select_copy_for_options):
    def inflate_expand_option(option_vals):
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
            nonexpanded_options = exp_options.copy()
            nonexpanded_options.pop('expand_options')

            expand_options = exp_options['expand_options']
            expand_values = list(itertools.product(*(
                [(option_key, option_val)
                 for option_val in inflate_expand_option(option_vals)]
                for (option_key, option_vals) in iteritems(expand_options)
            )))

            for expanded_options in expand_values:
                new_exp_name = exp_name_with_options(exp_name,
                                                     expanded_options)
                new_exp_options = dict(expanded_options, **nonexpanded_options)

                # handle selection copy_for_options
                if select_copy_for_options:
                    sliced_options = [o for o in expanded_options if
                                      o[0] not in select_copy_for_options]
                    for opts in expand_values:
                        if opts == expanded_options:
                            break
                        elif all(o in opts for o in sliced_options):
                            new_exp_options['selection_copy_from'] = \
                                exp_name_with_options(exp_name, opts)
                            break

                final_experiments[new_exp_name] = new_exp_options
        else:
            final_experiments[exp_name] = exp_options

    return final_experiments


def preprocess_steps(steps, paths, exp_options):
    def make_output_paths(options, keys):
        for key in keys:
            if key in options and not os.path.isabs(options[key]):
                options[key] = os.path.join(paths['output_dir'], options[key])

    steps = copy.deepcopy(steps)
    for step_options in steps:
        if step_options['type'] == 'select':
            step_options.update(paths)
        elif step_options['type'] == 'kmers':
            step_options['fasta_output_dir'] = paths['fasta_output_dir']
            if step_options['k'] == 'from_options':
                step_options['k'] = exp_options['k']
            make_output_paths(step_options, ['output_file'])
        elif step_options['type'] == 'distances':
            make_output_paths(step_options, ['input_file', 'output_prefix'])
        elif step_options['type'] == 'mds':
            make_output_paths(step_options, ['dists_file', 'output_file'])
        elif step_options['type'] == 'classify':
            step_options['metadata_file'] = paths['metadata_output_file']
            make_output_paths(step_options, ['features_file', 'output_file'])

    return steps


def make_aws_args(settings):
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


def validate_schema(data, schema_name):
    with open(os.path.normpath(os.path.join(
                  os.path.dirname(__file__), '..', 'schemas',
                  schema_name + '.json'
              ))) as schema:
        try:
            jsonschema.validate(data, json.load(schema))
        except Exception as e:
            e.message = ('error while validating {}: {}'
                         .format(schema_name, e.message))


def validate_job_options(options):
    validate_schema(options, 'job_options')


def load_metadata(metadata_dir, name):
    with open(os.path.join(metadata_dir, name + '.json'), 'r') as f:
        metadata = json.load(f)
    return metadata


def run_experiment_steps(steps, exp_options):
    for i, step_options in enumerate(steps):
        step_desc = "step '{}' ({}/{})".format(step_options['type'], i+1,
                                               len(steps))
        with job_utils.log_step(step_desc, start_stars=True):
            step_runners[step_options['type']](step_options, exp_options)


def run(args):
    job_options = YAML(typ='safe').load(args.job_file)
    validate_job_options(job_options)

    settings = YAML(typ='safe').load(args.settings_file)
    validate_schema(settings, 'settings')

    local_dirs = settings['local_dirs']
    job_name = job_options['name']

    experiments = job_options['experiments']
    if isinstance(experiments, six.string_types):
        paths = experiment_paths(local_dirs, job_name, '')
        experiments = job_utils.call_string_extended_lambda(
            experiments, load_metadata=functools.partial(load_metadata,
                                                         paths['metadata_dir'])
        )
    first_select = next(step for step in job_options['steps'] if
                        step['type'] == 'select')
    experiments = preprocess_experiments(experiments,
                                         first_select.get('copy_for_options'))

    if args.validate_only:
        print('INFO     options files validated successfully')
        return

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
                metadata = None
                if 'dataset' in exp_options and ('metadata' in
                                                 exp_options['dataset']):
                    metadata_name = exp_options['dataset']['metadata']
                    metadata = load_metadata(paths['metadata_dir'],
                                             metadata_name)
                exp_options['groups'] = job_utils.call_string_extended_lambda(
                    exp_options['groups'], dict(exp_options, **paths),
                    metadata,
                    load_metadata=functools.partial(load_metadata,
                                                    paths['metadata_dir'])
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

            # run steps
            run_experiment_steps(steps, exp_options)

            # finish file log
            file_logger.close()
            log.removeHandler(file_logger)
