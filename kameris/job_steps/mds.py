from __future__ import absolute_import, division, unicode_literals

import json
import logging
import kameris_formats
import numpy as np
import scipy.sparse.linalg as linalg


def mds(delta, dim):
    delta = delta.astype(float)
    (n, n) = delta.shape

    deltasq = delta**2
    deltatotals = np.sum(deltasq, axis=0)/n
    sumOfDelta = np.sum(deltatotals)/n

    # this way avoids temporaries (and is *much* faster than a loop)
    bMatr = deltasq
    bMatr -= deltatotals
    bMatr = bMatr.transpose()
    bMatr -= deltatotals
    bMatr = bMatr.transpose()
    bMatr += sumOfDelta
    bMatr *= -0.5

    (eigenvals, eigenvecs) = linalg.eigsh(bMatr, k=dim)
    if (eigenvals < 0).any():
        logging.getLogger('kameris.mds') \
               .warning('some eigenvalues were negative')

    # not sure why eigensystem is sorted in reverse order for eigsh...
    points = np.fliplr(np.dot(eigenvecs, np.diag(np.sqrt(eigenvals))))
    # TODO: see why the NaNs sometimes happen (maybe run dim+1?)
    return points[:, ~np.isnan(points).any(axis=0)]


def run_mds_step(options, exp_options):
    dists = kameris_formats.dist_reader.read_matrix(options['dists_file'])
    points = mds(dists, options['dimensions']).tolist()

    with open(options['output_file'], 'w') as outfile:
        json.dump(points, outfile)
