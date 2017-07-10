from __future__ import absolute_import, division, unicode_literals

import logging
import numpy as np
import re


# FASTA

def read_fasta(infile, include_other_letters=False):
    sequences = []

    currseq = []
    for line in infile:
        line = line.strip()
        if type(line) is bytes and type(line) is not str:
            line = line.decode()
        if not line or line[0] == '>':
            if currseq:
                sequences.append(''.join(currseq))
                currseq = []
        else:
            if not include_other_letters:
                line = re.sub('[^ACGT]', '', line)
            currseq.append(line)
    if currseq:
        sequences.append(''.join(currseq))

    return sequences


def import_fasta(filename):
    with open(filename, 'r') as infile:
        return read_fasta(infile)


def write_fasta(outfile, sequences):
    for seq in sequences:
        outfile.write('>\n')
        outfile.write(seq)
        outfile.write('\n')


def export_fasta(filename, sequences):
    with open(filename, 'w') as outfile:
        write_fasta(outfile, sequences)


# binary distance matrix

def import_dists(filename):
    # TODO: ugly hack, fix!
    if 'info' in filename:
        dtype_str = '<f4'
    elif 'manhat' in filename:
        dtype_str = '<u4'
    else:
        logging.getLogger('modmap.file_formats') \
               .warning('assuming matrix is 32-bit float')
        dtype_str = '<f4'

    dists = np.fromfile(filename, dtype=np.dtype(dtype_str))
    dists_len = int(np.sqrt(dists.size))
    dists = np.reshape(dists, (dists_len, dists_len))

    return dists
