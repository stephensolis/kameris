from __future__ import absolute_import, division, unicode_literals

import copy
import json
import os
import re
from six import iteritems
from tqdm import tqdm
import zipfile

# these may be used by pick_group_fn/postprocess_fn
import copy  # NOQA
from six.moves import range  # NOQA

from . import file_formats
from . import utils


def run_selection(options, exp_options):
    groups = exp_options['groups'].copy()

    # load selection functions
    selection_funcs = {}
    exec(re.sub('^lambda (.*):', 'def pick_group_fn(\\1):',
                options['pick_group']),
         selection_funcs)
    if 'postprocess' in options:
        exec(re.sub('^lambda (.*):', 'def postprocess_fn(\\1):',
                    options['postprocess']),
             selection_funcs)

    # run pick_group
    with utils.log_step('running pick_group'):
        pick_group_metadata = []
        all_metadata_cache = {}

        for group_name, group_options in iteritems(groups):
            group_options = group_options.copy()
            groups[group_name] = group_options

            group_options['name'] = group_name
            if 'dataset' not in group_options:
                group_options['dataset'] = exp_options['dataset']

            # fetch metadata
            all_metadata_filename = os.path.join(
                options['metadata_dir'],
                'metadata-{}.json'.format(group_options['dataset']['metadata'])
            )
            if all_metadata_filename in all_metadata_cache:
                all_metadata = all_metadata_cache[all_metadata_filename]
            else:
                with open(all_metadata_filename, 'r') as infile:
                    all_metadata = json.load(infile)
                all_metadata_cache[all_metadata_filename] = all_metadata

            # perform selection
            group_metadata = selection_funcs['pick_group_fn'](
                copy.deepcopy(all_metadata),
                copy.deepcopy(group_options)
            )
            for metadata_entry in group_metadata:
                metadata_entry['group'] = group_name
                pick_group_metadata.append(metadata_entry)

    utils.mkdir_p(options['fasta_output_dir'])

    # read, process, and write sequences
    with utils.log_step('processing metadata entries'):
        final_metadata = []
        archive_cache = {}
        file_counter = 1

        for metadata_entry in tqdm(pick_group_metadata, mininterval=1,
                                   file=utils.LoggerFileAdapter('modmap')):
            group_options = groups[metadata_entry['group']]

            # open archive file
            archive_filename = os.path.join(
                options['archives_dir'],
                group_options['dataset']['archive'] + '.zip'
            )
            if archive_filename in archive_cache:
                archive = archive_cache[archive_filename]
            else:
                archive = zipfile.ZipFile(archive_filename)
                archive_cache[archive_filename] = archive

            # find path for file in archive
            if 'filename' in metadata_entry:
                filename = metadata_entry['filename']
            else:
                filename = metadata_entry['id'] + '.fasta'
                if 'archive_folder' in group_options['dataset']:
                    filename = '{}/{}'.format(
                        group_options['dataset']['archive_folder'], filename
                    )

            # read file
            sequence_file = archive.open(filename)
            file_sequences = file_formats.read_fasta(sequence_file)

            # run postprocess if required
            if 'postprocess' in options:
                new_metadata, sequences_list = zip(
                    *selection_funcs['postprocess_fn'](
                        copy.deepcopy(metadata_entry), file_sequences
                    )
                )
            else:
                new_metadata = [metadata_entry]
                sequences_list = [file_sequences]
            final_metadata.extend(new_metadata)

            # write fasta files
            for sequences, final_metadata_entry in zip(sequences_list,
                                                       new_metadata):
                filename = str(file_counter).zfill(10) + '.fasta'
                file_path = os.path.join(options['fasta_output_dir'], filename)

                final_metadata_entry['filename'] = filename
                file_formats.export_fasta(file_path, sequences)
                file_counter += 1

    # write metadata
    with utils.log_step('writing metadata file'):
        with open(options['metadata_output_file'], 'w') as outfile:
            json.dump(final_metadata, outfile)
