from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import base64
import collections
import json
import os
import re
from six import iteritems
import subprocess
from tabulate import tabulate

from ..job_steps._classifiers import classifier_names
from ..utils import fs_utils


all_classifiers = set(classifier_names)


def natural_sort_key(string):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]


def run(args):
    accuracy_key = 'top{}'.format(args.top_n)

    def accuracy_for_classifier(classifier_results):
        return classifier_results[accuracy_key]['accuracy'] * 100

    run_stats = {}

    for run_name in os.listdir(args.job_dir):
        curr_path = os.path.join(args.job_dir, run_name)
        if not os.path.isdir(curr_path):
            continue

        base_run_name = re.sub('-k=[0-9]+', '', run_name)
        run_k = re.search('-k=([0-9]+)', run_name)
        if run_k is None:
            raise RuntimeError('Run name {} does not have a parameter k, '
                               'which is currently unsupported'
                               .format(run_name))
        run_k = int(run_k.group(1))

        if base_run_name not in run_stats:
            with open(os.path.join(curr_path, 'metadata.json')) as f:
                metadata = json.load(f)
                groups = (x['group'] for x in metadata)

            dists = [filename[15:-5]
                     for filename in os.listdir(curr_path)
                     if filename.startswith('classification-')
                     and filename.endswith('.json')
                     and os.path.isfile(os.path.join(curr_path, filename))]

            run_stats[base_run_name] = {
                'classes': collections.Counter(groups),
                'dists': dists,
                'classifier_counts': collections.defaultdict(int),
                'ks': set(),
                'best_classifier': {'accuracy': 0},
                'best_classifier_by_k': {
                    dist: collections.defaultdict(lambda: {'accuracy': 0})
                    for dist in dists
                }
            }

        curr_stats = run_stats[base_run_name]
        curr_stats['ks'].add(run_k)

        dist_results = {}
        for dist_name in curr_stats['dists']:
            with open(os.path.join(curr_path, 'classification-{}.json'
                                              .format(dist_name))) as f:
                dist_results[dist_name] = json.load(f)

        for dist_name, results in iteritems(dist_results):
            for classifier, classifier_results in iteritems(results):
                if accuracy_key not in classifier_results:
                    continue

                curr_stats['classifier_counts'][classifier] += 1
                accuracy = accuracy_for_classifier(classifier_results)

                if (accuracy > curr_stats['best_classifier']['accuracy'] or
                    (accuracy == curr_stats['best_classifier']['accuracy']
                     and run_k < curr_stats['best_classifier']['k'])):
                    curr_stats['best_classifier'] = {
                        'accuracy': accuracy,
                        'confusion_matrix':
                            classifier_results['confusion_matrix'],

                        'class_order': classifier_results['classes'],
                        'dist': dist_name,
                        'k': run_k,
                        'classifier': classifier,

                        'metadata_file': os.path.join(
                            curr_path, 'metadata.json'),
                        'classification_file': os.path.join(
                            curr_path,
                            'classification-{}.json'.format(dist_name)),
                        'mds_file': os.path.join(
                            curr_path, 'mds10-{}.json'.format(dist_name))
                    }

                    curr_stats['best_k_classifiers'] = {
                        curr_dist: {
                            curr_classifier: accuracy_for_classifier(
                                curr_classifier_results
                            )
                            for curr_classifier, curr_classifier_results
                            in iteritems(curr_results)
                            if accuracy_key in curr_classifier_results
                        }
                        for curr_dist, curr_results
                        in iteritems(dist_results)
                    }

                best_by_k_stats = curr_stats['best_classifier_by_k'][dist_name]
                if accuracy > best_by_k_stats[run_k]['accuracy']:
                    best_by_k_stats[run_k] = {
                        'accuracy': accuracy,
                        'classifier': classifier
                    }

    exp_names = sorted(run_stats.keys(), key=natural_sort_key)
    for exp_name in exp_names:
        curr_stats = run_stats[exp_name]
        best_stats = curr_stats['best_classifier']
        if len(curr_stats['classes']) <= args.top_n:
            continue

        print()
        print('Experiment:', exp_name)
        print()

        exp_classifiers = set(curr_stats['classifier_counts'].keys())
        always_classifiers = {
            name for name, count in iteritems(curr_stats['classifier_counts'])
            if count == len(curr_stats['ks'])*len(curr_stats['dists'])
        }
        print('These classifiers ran every time: [{}]'
              .format(', '.join(always_classifiers)))
        print('These classifiers ran sometimes but not always: [{}]'
              .format(', '.join(exp_classifiers - always_classifiers)))
        print('These classifiers did not run: [{}]'
              .format(', '.join(all_classifiers - exp_classifiers)))
        print()

        print('Classes:')
        for class_name in best_stats['class_order']:
            print('{} ({})'
                  .format(class_name, curr_stats['classes'][class_name]))
        print()

        print('Best accuracy: {accuracy:.2f}% (k={k}, {dist}, {classifier})'
              .format(**best_stats))
        print('Confusion matrix:')
        print(tabulate(
            best_stats['confusion_matrix']
        ))
        print()

        best_by_k = curr_stats['best_classifier_by_k']
        print('Best classifier by k:')
        print(tabulate(
            [[k] + [val for dist_name in curr_stats['dists']
                    for val in ([best_by_k[dist_name][k]['accuracy'],
                                 best_by_k[dist_name][k]['classifier']]
                                if 'classifier' in best_by_k[dist_name][k]
                                else ['N/A', 'N/A'])]
             for k in curr_stats['ks']],
            ['k'] + [header for dist_name in curr_stats['dists']
                     for header in [dist_name + '-accuracy',
                                    dist_name + '-classifier']],
            floatfmt='.2f'
        ))
        print()

        best_for_k = curr_stats['best_k_classifiers']
        best_classifiers = set(c for classifier_results in best_for_k.values()
                               for c in classifier_results.keys())
        print('Classifiers for k={}:'
              .format(best_stats['k']))
        print(tabulate(
            [[c] + [best_for_k[dist_name][c]
                    if c in best_for_k[dist_name] else 'N/A'
                    for dist_name in curr_stats['dists']]
             for c in best_classifiers],
            ['classifier'] + curr_stats['dists'],
            floatfmt='.2f'
        ))
        print()

        if args.plot_output_dir is not None:
            num_classes = len(curr_stats['classes'])
            if num_classes > 10:
                print('Warning: skipping plot generation because there are '
                      'too many classes ({} > 10)'.format(num_classes))
            else:
                base_output_path = os.path.join(
                    args.plot_output_dir, os.path.basename(args.job_dir)
                )
                fs_utils.mkdir_p(base_output_path)
                base_output_filename = os.path.join(
                    base_output_path, '{}-k={k}-{dist}-{classifier}'
                                      .format(exp_name, **best_stats)
                )
                subprocess.call(
                    'wolframscript "{}" {}'.format(
                        os.path.normpath(os.path.join(
                            os.path.dirname(__file__), '..', 'scripts',
                            'make_plots.wls'
                        )),
                        base64.b64encode(json.dumps({
                            'accuracy_type': accuracy_key,
                            'classifier_name': best_stats['classifier'],
                            'metadata_file': best_stats['metadata_file'],
                            'classification_file':
                                best_stats['classification_file'],
                            'mds_file': best_stats['mds_file'],
                            'output_file': base_output_filename + '-plots.nb',
                            'svg_output_file':
                                base_output_filename + '-plot2d.svg',
                            'png_output_file':
                                base_output_filename + '-plot2d.png'
                        }))
                    ),
                    shell=True
                )

        print('='*80)

    print()
    print('Experiment summary:')
    print(tabulate(
        [[exp_name, run_stats[exp_name]['best_classifier']['accuracy'],
          'k={k}, {dist}, {classifier}'
          .format(**run_stats[exp_name]['best_classifier'])]
         for exp_name in exp_names
         if len(run_stats[exp_name]['classes']) > args.top_n],
        ['experiment', 'best accuracy', 'run info'],
        floatfmt='.2f'
    ))
    print()
