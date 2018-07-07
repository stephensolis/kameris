from __future__ import absolute_import, division, unicode_literals


def main():
    from .utils import launcher_utils
    launcher_utils.ensure_running_in_shell()

    # this fixes ctrl+c on Windows because of scipy
    import os
    os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

    import argparse
    from six import iteritems

    from .subcommands import subcommands
    from . import __version__

    parser = argparse.ArgumentParser(
        description='A fast, user-friendly analysis and evaluation pipeline '
                    'for some DNA sequence classification tasks.'
    )
    parser.add_argument('-v', '--version', action='version',
                        version='This is Kameris ' + __version__)
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True
    for cmd, cmd_settings in iteritems(subcommands):
        subparser = subparsers.add_parser(
            cmd, help=cmd_settings['description'],
            description=cmd_settings['description']
        )
        cmd_settings['setup_args'](subparser)
        subparser.set_defaults(module_name=cmd_settings['module_name'])

    import importlib

    try:
        args = parser.parse_args()
        run_module = importlib.import_module(
            '.subcommands.' + args.module_name, 'kameris'
        )
        run_module.run(args)
    except Exception as e:
        import logging
        import sys
        import traceback

        log = logging.getLogger('kameris')
        message = 'an unexpected error occurred: {}: {}'.format(
            type(e).__name__,
            (e.message if hasattr(e, 'message') else '') or str(e)
        )
        report_message = (
            'if you believe this is a bug, please report it at '
            'https://github.com/stephensolis/kameris/issues and include ALL '
            'the following text:\n') + ''.join(traceback.format_exc())
        if log.handlers:
            log.error(message)
            log.error(report_message)
        else:
            print('ERROR    ' + message)
            print('ERROR    ' + report_message)
        sys.exit(1)


if __name__ == '__main__':
    main()
