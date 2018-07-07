from __future__ import absolute_import, division, unicode_literals

import argparse
import os


def argparse_positive_int(num):
    num = int(num)
    if num <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    else:
        return num


def argparse_check_dir(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(path + ' is not a directory')
    else:
        return path


def run_job_setup_args(parser):
    parser.add_argument('job_file', type=argparse.FileType('r'),
                        help='job description YAML file')
    parser.add_argument('settings_files', nargs='+',
                        type=argparse.FileType('r'),
                        help='run settings YAML files (in case of duplicated '
                             'settings keys, the one in the last file takes '
                             'priority)')


def summarize_setup_args(parser):
    parser.add_argument('job_dir', type=argparse_check_dir,
                        help='the base directory of the job output')
    parser.add_argument('plot_output_dir', nargs='?', type=argparse_check_dir,
                        help='if specified, saves MDS plots to this directory '
                             '(requires an MDS job step and Mathematica '
                             'installed)')
    parser.add_argument('--top-n', type=argparse_positive_int, default=1,
                        help='the top-N results by confidence to accept as a '
                             'correct prediction (defaults to top-1)')


subcommands = {
    'run-job': {
        'module_name': 'run_job',
        'setup_args': run_job_setup_args,
        'description': 'Executes a job description file.'
    },
    'summarize': {
        'module_name': 'summarize',
        'setup_args': summarize_setup_args,
        'description': 'Prints summary information from a classification job '
                       'run.'
    },
    # 'classify': {
    #     'module_name': 'classify',
    #     'setup_args': classify_setup_args,
    #     'description': 'Runs sequences through a trained model.'
    # }
}
