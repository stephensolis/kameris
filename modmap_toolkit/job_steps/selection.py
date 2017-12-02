from __future__ import absolute_import, division, unicode_literals

import copy
import json
import os
from six import iteritems
from tqdm import tqdm
import zipfile

# these may be used by pick_group_fn/postprocess_fn
from six.moves import range  # NOQA

from utils import file_formats, fs_utils, job_utils


def run_select_step(options, exp_options):
    groups = exp_options['groups'].copy()

    # run pick_group
    with job_utils.log_step('running pick_group'):
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
                group_options['dataset']['metadata'] + '.json'
            )
            if all_metadata_filename in all_metadata_cache:
                all_metadata = all_metadata_cache[all_metadata_filename]
            else:
                with open(all_metadata_filename, 'r') as infile:
                    all_metadata = json.load(infile)
                all_metadata_cache[all_metadata_filename] = all_metadata

            # perform selection
            group_metadata = job_utils.call_string_extended_lambda(
                options['pick_group'],
                copy.deepcopy(all_metadata),
                copy.deepcopy(group_options)
            )
            for metadata_entry in group_metadata:
                metadata_entry['group'] = group_name
                pick_group_metadata.append(metadata_entry)

    fs_utils.mkdir_p(options['fasta_output_dir'])

    # read, process, and write sequences
    with job_utils.log_step('processing metadata entries'):
        final_metadata = []
        archive_cache = {}
        file_counter = 1

        for metadata_entry in tqdm(pick_group_metadata, mininterval=1,
                                   file=job_utils.LoggerFileAdapter('modmap')):
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

            # fetch sequences
            if 'filenames' in metadata_entry and 'postprocess' in options:
                file_sequences = [
                    file_formats.read_fasta(archive.open(filename))
                    for filename in metadata_entry['filenames']
                ]
            else:
                # find path for file in archive
                if 'filename' in metadata_entry:
                    filename = metadata_entry['filename']
                else:
                    filename = metadata_entry['id'] + '.fasta'
                    if 'archive_folder' in group_options['dataset']:
                        filename = '{}/{}'.format(
                            group_options['dataset']['archive_folder'],
                            filename
                        )

                # read file
                file_sequences = file_formats.read_fasta(
                    archive.open(filename)
                )

            # run postprocess if required
            if 'postprocess' in options:
                new_metadata, sequences_list = zip(
                    *job_utils.call_string_extended_lambda(
                        options['postprocess'],
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
    with job_utils.log_step('writing metadata file'):
        with open(options['metadata_output_file'], 'w') as outfile:
            json.dump(final_metadata, outfile)
