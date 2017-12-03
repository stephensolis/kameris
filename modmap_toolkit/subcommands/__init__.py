from __future__ import absolute_import, division, unicode_literals

from . import run_job
from . import summarize


subcommands = {
    'run-job': {
        'run': run_job.run,
        'setup_args': run_job.setup_args
    },
    'summarize': {
        'run': summarize.run,
        'setup_args': summarize.setup_args
    }
}
