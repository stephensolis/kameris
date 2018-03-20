from __future__ import absolute_import, division, unicode_literals

import os
import platform
import x86cpu

from . import command


def cpu_suffix():
    if x86cpu.cpuid(7)['ebx'] & (1 << 5):
        return 'avx2'
    else:
        return 'sse41'


def platform_suffix():
    if platform.system() == 'Windows':
        return 'windows'
    elif platform.system() == 'Linux':
        return 'linux'
    elif platform.system() == 'Darwin':
        return 'mac'


def executable_suffix():
    result = '_' + platform_suffix() + '_' + cpu_suffix()
    if platform.system() == 'Windows':
        result += '.exe'
    return result


def binary_path(bin_name):
    return os.path.join(os.path.dirname(__file__), '..', 'scripts',
                        bin_name + executable_suffix())


def run_mmg_kmers(options, exp_options):
    command.run_command_step({
        'command': '"{}" cgr "{}" "{}" {} {}'.format(
                        binary_path('generation_cgr'),
                        options['fasta_output_dir'], options['output_file'],
                        options['k'], options['bits_per_element'])
    }, {})


def run_mmg_dists(options, exp_options):
    command.run_command_step({
        'command': '"{}" "{}" "{}" {}'.format(
                        binary_path('generation_dists'),
                        options['input_file'], options['output_prefix'],
                        ','.join(options['distances']))
    }, {})
