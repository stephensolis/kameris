from __future__ import absolute_import, division, unicode_literals

import re
from six.moves import zip


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
