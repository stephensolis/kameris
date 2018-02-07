from __future__ import absolute_import, division, unicode_literals

import os
import platform

from . import command


def executable_suffix():
    if platform.system() == 'Windows':
        return '.exe'
    elif platform.system() == 'Linux':
        return '_linux'
    elif platform.system() == 'Darwin':
        return '_mac'


def run_mmg_kmers(options, exp_options):
    command.run_command_step({
        'command': '"{}" cgr "{}" "{}" {} {}'.format(
                        os.path.join(os.path.dirname(__file__),
                                     '..', 'scripts',
                                     'generation_cgr' + executable_suffix()),
                        options['fasta_output_dir'], options['output_file'],
                        options['k'], options['bits_per_element'])
    }, {})


def run_mmg_dists(options, exp_options):
    command.run_command_step({
        'command': '"{}" "{}" "{}" {}'.format(
                        os.path.join(os.path.dirname(__file__),
                                     '..', 'scripts',
                                     'generation_dists' + executable_suffix()),
                        options['input_file'], options['output_prefix'],
                        ','.join(options['distances']))
    }, {})
