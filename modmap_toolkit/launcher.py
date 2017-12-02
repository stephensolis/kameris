from __future__ import absolute_import, division, unicode_literals


import argparse

from .subcommands import ...
from .utils import launcher_utils


def main():
    launcher_utils.ensure_running_in_shell()


if __name__ == '__main__':
    main()
