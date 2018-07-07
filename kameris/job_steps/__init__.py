from __future__ import absolute_import, division, unicode_literals

from . import backend
from . import classify
from . import mds
from . import selection


step_runners = {
    'classify': classify.run_classify_step,
    'distances': backend.run_backend_dists,
    'kmers': backend.run_backend_kmers,
    'mds': mds.run_mds_step,
    'select': selection.run_select_step
}
