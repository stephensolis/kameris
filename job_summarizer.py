from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import re


all_classifiers = {
    '10-nearest-neighbors', 'linear-svm', 'quadratic-svm',
    'gaussian-naive-bayes', 'decision-tree', 'random-forest',
    'logistic-regression', 'nearest-centroid-mean',
    'nearest-centroid-median'
}
accuracy_key = 'top1'


def natural_sort_key(string):
    """See http://www.codinghorror.com/blog/archives/001018.html"""
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string)]


if __name__ == '__main__':
    import base64
    import collections
    import json
    import os
    from six import iteritems
    import subprocess
    import sys
    import tabulate

    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('usage: job_summarizer.py <job directory> (<output directory>)')
        sys.exit(1)

    run_stats = {}

    for run_name in os.listdir(sys.argv[1]):
        curr_path = os.path.join(sys.argv[1], run_name)
        if os.path.isdir(curr_path):
            base_run_name = re.sub('-k=[0-9]+', '', run_name)
            run_k = int(re.search('-k=([0-9]+)', run_name).group(1))

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
                    curr_stats['classifier_counts'][classifier] += 1
                    accuracy = classifier_results[accuracy_key]['accuracy']*100

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
                                curr_classifier:
                                    curr_classifier_results[accuracy_key]['accuracy']*100
                                for curr_classifier, curr_classifier_results
                                in iteritems(curr_results)
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
        print(tabulate.tabulate(
            best_stats['confusion_matrix']
        ))
        print()

        best_by_k = curr_stats['best_classifier_by_k']
        print('Best classifier by k:')
        print(tabulate.tabulate(
            [[k] + [val for dist_name in curr_stats['dists']
                    for val in [best_by_k[dist_name][k]['accuracy'],
                                best_by_k[dist_name][k]['classifier']]]
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
        print(tabulate.tabulate(
            [[c] + [best_for_k[dist_name][c]
                    if c in best_for_k[dist_name] else 'N/A'
                    for dist_name in curr_stats['dists']]
             for c in best_classifiers],
            ['classifier'] + curr_stats['dists'],
            floatfmt='.2f'
        ))
        print()

        if len(sys.argv) == 3:
            base_output_filename = os.path.join(
                sys.argv[2],
                '{}-k={k}-{dist}-{classifier}'.format(exp_name, **best_stats)
            )
            subprocess.call(
                'wolframscript "{}" {}'.format(
                    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'client', 'make_plots.wls'),
                    base64.b64encode(json.dumps({
                        'accuracy_type': accuracy_key,
                        'classifier_name': best_stats['classifier'],
                        'metadata_file': best_stats['metadata_file'],
                        'classification_file':
                            best_stats['classification_file'],
                        'mds_file': best_stats['mds_file'],
                        'output_file': base_output_filename + '-plots.nb'
                    }))
                )
            )

        print('='*80)

    print()
    print('Experiment summary:')
    print(tabulate.tabulate(
        [[exp_name, run_stats[exp_name]['best_classifier']['accuracy'],
          'k={k}, {dist}, {classifier}'
          .format(**run_stats[exp_name]['best_classifier'])]
         for exp_name in exp_names],
        ['experiment', 'best accuracy', 'run info'],
        floatfmt='.2f'
    ))
    print()
