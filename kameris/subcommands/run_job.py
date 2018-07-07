from __future__ import (
    absolute_import, division, print_function, unicode_literals)

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

from ..job_steps import step_runners
from ..utils import download_utils, fs_utils, job_utils


def experiment_paths(local_dirs, job_name, exp_name, urls_file):
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
                                              'rerun_experiment.yml'),
        'urls_file': urls_file
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


def preprocess_steps(steps, paths, exp_options, disable_avx):
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
            step_options['disable_avx'] = disable_avx
            if step_options['k'] == 'from_options':
                step_options['k'] = exp_options['k']
            make_output_paths(step_options, ['output_file'])
        elif step_options['type'] == 'distances':
            step_options['disable_avx'] = disable_avx
            make_output_paths(step_options, ['input_file', 'output_prefix'])
        elif step_options['type'] == 'mds':
            make_output_paths(step_options, ['dists_file', 'output_file'])
        elif step_options['type'] == 'classify':
            step_options['metadata_file'] = paths['metadata_output_file']
            make_output_paths(step_options, ['features_file', 'output_file'])
            generation_opts = next(
                (step for step in steps if step['type'] == 'kmers' and
                 step['output_file'] == step_options['features_file']),
                None
            )
            if generation_opts:
                step_options['generation_options'] = {
                    k: generation_opts[k] for k in
                    {'mode', 'k', 'bits_per_element'}
                }

    return steps


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
            raise e


def validate_job_options(options):
    validate_schema(options, 'job_options')

    # check lambdas under experiments
    if isinstance(options['experiments'], six.string_types):
        job_utils.parse_multiline_lambda_str(options['experiments'])
    else:
        for exp_opts in options['experiments'].values():
            if isinstance(exp_opts['groups'], six.string_types):
                job_utils.parse_multiline_lambda_str(exp_opts['groups'])

    # check select step
    select_steps = [s for s in options['steps'] if s['type'] == 'select']
    if len(select_steps) > 1:
        raise Exception('at most one step of type select is allowed in a job')
    elif select_steps:
        select_step = select_steps[0]
        job_utils.parse_multiline_lambda_str(select_step['pick_group'])
        if 'postprocess' in select_step:
            job_utils.parse_multiline_lambda_str(select_step['postprocess'])


def load_metadata(metadata_dir, urls_file, name):
    file_path = os.path.join(metadata_dir, name + '.json')
    if not os.path.exists(file_path):
        download_utils.download_file(
            download_utils.url_for_file(file_path, urls_file, 'metadata'),
            file_path
        )
    with open(file_path, 'r') as f:
        metadata = json.load(f)
    return metadata


def run_experiment_steps(steps, exp_options):
    for i, step_options in enumerate(steps):
        step_desc = "step '{}' ({}/{})".format(step_options['type'], i+1,
                                               len(steps))
        with job_utils.log_step(step_desc, start_stars=True):
            step_runners[step_options['type']](step_options, exp_options)


def run(args):
    job_options = YAML(typ='safe').load(
        download_utils.read_file_or_url(args.job_file)
    )
    validate_job_options(job_options)

    settings = YAML(typ='safe').load(
        download_utils.read_file_or_url(args.settings_file)
    )
    validate_schema(settings, 'settings')

    if args.validate_only:
        if args.urls_file:
            validate_schema(YAML(typ='safe').load(
                download_utils.read_file_or_url(args.urls_file)
            ), 'file_urls')
        print('INFO     options files validated successfully')
        return

    local_dirs = settings['local_dirs']
    job_name = job_options['name']

    experiments = job_options['experiments']
    if isinstance(experiments, six.string_types):
        paths = experiment_paths(local_dirs, job_name, '')
        experiments = job_utils.parse_multiline_lambda_str(
            experiments, load_metadata=functools.partial(
                load_metadata, paths['metadata_dir'], args.urls_file
            )
        )()
    first_select = next((step for step in job_options['steps'] if
                        step['type'] == 'select'), {})
    experiments = preprocess_experiments(experiments,
                                         first_select.get('copy_for_options'))

    log, formatter = job_utils.setup_logging(job_name, settings)

    for i, (exp_name, exp_options) in enumerate(iteritems(experiments)):
        with job_utils.log_step("experiment '{}' ({}/{})"
                                .format(exp_name, i+1, len(experiments)),
                                start_stars=True):
            exp_options = exp_options.copy()
            exp_options['experiment_name'] = exp_name

            # get ready
            paths = experiment_paths(local_dirs, job_name, exp_name,
                                     args.urls_file)
            steps = preprocess_steps(job_options['steps'], paths, exp_options,
                                     args.disable_avx)
            if isinstance(exp_options['groups'], six.string_types):
                metadata = None
                if 'dataset' in exp_options and ('metadata' in
                                                 exp_options['dataset']):
                    metadata_name = exp_options['dataset']['metadata']
                    metadata = load_metadata(paths['metadata_dir'],
                                             args.urls_file, metadata_name)
                exp_options['groups'] = job_utils.parse_multiline_lambda_str(
                    exp_options['groups'],
                    load_metadata=functools.partial(
                        load_metadata, paths['metadata_dir'], args.urls_file
                    )
                )(dict(exp_options, **paths), metadata)
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
