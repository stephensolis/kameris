from __future__ import absolute_import, division, unicode_literals

from . import classify
from . import command
from . import mds
from . import mmg
from . import selection


step_runners = {
    'classify': classify.run_classify_step,
    'command': command.run_command_step,
    'kmers': mmg.run_mmg_kmers,
    'distances': mmg.run_mmg_dists,
    'mds': mds.run_mds_step,
    'select': selection.run_select_step
}
