from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from client import client

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print('usage: job_runner.py <job file> <settings file>')
        sys.exit(1)

    client.run_job(sys.argv[1], sys.argv[2])
