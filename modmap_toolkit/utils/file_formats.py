from __future__ import absolute_import, division, unicode_literals

import logging
import numpy as np
import re


# FASTA

def read_fasta(infile, include_other_letters=False, return_headers=False):
    sequences = []
    if return_headers:
        headers = []

    currseq = []
    for line in infile:
        line = line.strip()
        if isinstance(line, bytes) and str != bytes:
            line = line.decode()
        if not line or line[0] == '>':
            if return_headers and line[0] == '>':
                headers.append(line)
            if currseq:
                sequences.append(''.join(currseq))
                currseq = []
        else:
            if not include_other_letters:
                line = re.sub('[^ACGT]', '', line)
            currseq.append(line)
    if currseq:
        sequences.append(''.join(currseq))

    if return_headers:
        return sequences, headers
    else:
        return sequences


def import_fasta(filename, **kwargs):
    with open(filename, 'r') as infile:
        return read_fasta(infile, **kwargs)


def write_fasta(outfile, sequences, headers=iter(str, 0)):
    for header, seq in zip(headers, sequences):
        outfile.write('>' + header + '\n')
        outfile.write(seq)
        outfile.write('\n')


def export_fasta(filename, sequences, **kwargs):
    with open(filename, 'w') as outfile:
        write_fasta(outfile, sequences, **kwargs)


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

    return np.reshape(dists, (dists_len, dists_len))


# binary CGRs

def read_cgrs(infile):
    [cgr_dtype] = np.fromfile(infile, dtype=np.dtype('<u1'), count=1)
    if cgr_dtype == 16:
        dtype_str = '<u2'
    elif cgr_dtype == 32:
        dtype_str = '<u4'

    [num_cgrs] = np.fromfile(infile, dtype=np.dtype('<u8'), count=1)
    cgrs = np.fromfile(infile, dtype=np.dtype(dtype_str))

    return np.reshape(cgrs, (num_cgrs, int(len(cgrs) / num_cgrs)))


def import_cgrs(filename):
    with open(filename, 'rb') as infile:
        return read_cgrs(infile)
