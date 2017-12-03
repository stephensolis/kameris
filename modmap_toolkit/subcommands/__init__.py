from __future__ import absolute_import, division, unicode_literals

from . import run_job
from . import summarize


subcommands = {
    'run-job': {
        'run': run_job.run,
        'setup_args': run_job.setup_args,
        'description': 'Executes a job description file.'
    },
    'summarize': {
        'run': summarize.run,
        'setup_args': summarize.setup_args,
        'description': 'Prints summary information from a classification job '
                       'run.'
    },
    # 'classify': {
    #     'run': classify.run,
    #     'setup_args': classify.setup_args,
    #     'description': 'Runs sequences through a trained model.'
    # }
}
