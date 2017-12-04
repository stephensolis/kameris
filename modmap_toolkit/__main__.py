from __future__ import absolute_import, division, unicode_literals


def main():
    from .utils import launcher_utils
    launcher_utils.ensure_running_in_shell()

    import argparse
    from six import iteritems

    from .subcommands import subcommands

    parser = argparse.ArgumentParser(
        description='Generation, analysis, and evaluation tools for Molecular '
                    'Distance Maps.'
    )
    subparsers = parser.add_subparsers()
    for cmd, cmd_settings in iteritems(subcommands):
        subparser = subparsers.add_parser(
            cmd, help=cmd_settings['description'],
            description=cmd_settings['description']
        )
        cmd_settings['setup_args'](subparser)
        subparser.set_defaults(module_name=cmd_settings['module_name'])

    import importlib

    args = parser.parse_args()
    run_module = importlib.import_module('.subcommands.' + args.module_name,
                                         'modmap_toolkit')
    run_module.run(args)


if __name__ == '__main__':
    main()
