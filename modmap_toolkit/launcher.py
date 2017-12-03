from __future__ import absolute_import, division, unicode_literals


import argparse
from six import iteritems

from .subcommands import subcommands
from .utils import launcher_utils


def main():
    launcher_utils.ensure_running_in_shell()

    parser = argparse.ArgumentParser(
        description='Generation, analysis, and evaluation tools for Molecular '
                    'Distance Maps.'
    )
    subparsers = parser.add_subparsers()
    for cmd, cmd_settings in iteritems(subcommands):
        subparser = subparsers.add_parser(cmd)
        cmd_settings['setup_args'](subparser)
        subparser.set_defaults(run=cmd_settings['run'])

    args = parser.parse_args()
    args.run(args)
