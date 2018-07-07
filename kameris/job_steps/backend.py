from __future__ import absolute_import, division, unicode_literals

import kameris_formats
import os
import platform
import x86cpu

from . import _command
from ..utils import job_utils
from ..utils.platform_utils import platform_name


def cpu_suffix(disable_avx):
    if not disable_avx and x86cpu.cpuinfo.X86Info().supports_avx2:
        return 'avx2'
    else:
        return 'sse41'


def executable_suffix(disable_avx):
    result = '_' + platform_name() + '_' + cpu_suffix(disable_avx)
    if platform.system() == 'Windows':
        result += '.exe'
    return result


def binary_path(bin_name, disable_avx):
    return os.path.normpath(os.path.join(
        os.path.dirname(__file__), '..', 'scripts',
        bin_name + executable_suffix(disable_avx)
    ))


def run_backend_kmers(options, exp_options):
    _command.run_command_step({
        'command': '"{}" cgr "{}" "{}" {} {}'.format(
                        binary_path('generation_cgr', options['disable_avx']),
                        options['fasta_output_dir'], options['output_file'],
                        options['k'], options['bits_per_element'])
    }, {})

    # convert counts to frequencies if desired
    if options['mode'] == 'frequencies':
        with job_utils.log_step('frequency-normalizing CGRs'):
            reader = kameris_formats.repr_reader(options['output_file'])
            cgrs = []
            for i in range(reader.count):
                cgr = reader.read_matrix(i)
                cgrs.append(cgr/cgr.sum())

            writer = kameris_formats.repr_writer(
                options['output_file'], cgrs[0], len(cgrs), create_file=True
            )
            for cgr in cgrs:
                writer.write_matrix(cgr)
            writer.file.close()


def run_backend_dists(options, exp_options):
    _command.run_command_step({
        'command': '"{}" "{}" "{}" {}'.format(
                        binary_path('generation_dists',
                                    options['disable_avx']),
                        options['input_file'], options['output_prefix'],
                        ','.join(options['distances']))
    }, {})
