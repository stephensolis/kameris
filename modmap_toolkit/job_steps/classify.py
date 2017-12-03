from __future__ import absolute_import, division, unicode_literals

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import sklearn.metrics

from collections import defaultdict
import json
import logging
import numpy as np
from six import iteritems
from six.moves import range
import stopit
import timeit

from .classifiers import classifiers_by_name
from ..utils import file_formats, job_utils


def classification_run(predictor_factory, features, point_classes, all_classes,
                       train_indexes, test_indexes, normalize_features=True):
    num_features = len(features[0])
    num_test_points = len(test_indexes)
    train_features = features[train_indexes, :]
    train_classes = point_classes[train_indexes]
    test_features = features[test_indexes, :]
    test_realclasses = point_classes[test_indexes]

    if normalize_features:
        # scale each feature dimension to 0 mean and unit variance
        normalizer = StandardScaler()
        train_features = normalizer.fit_transform(train_features)
        test_features = normalizer.transform(test_features)

        # reduce dimensionality to 1/10 of its original
        # TODO: make this adjustable
        dim_reducer = PCA(n_components=int(np.ceil(num_features/10)))
        train_features = dim_reducer.fit_transform(train_features)
        test_features = dim_reducer.transform(test_features)

    predictor = predictor_factory()
    start_time = timeit.default_timer()
    predictor.fit(train_features, train_classes)
    train_end_time = timeit.default_timer()

    if hasattr(predictor, 'predict_proba'):
        test_expprobs = predictor.predict_proba(test_features)
        test_end_time = timeit.default_timer()

        num_topN = len(predictor.classes_) - 1
        test_expclasses_ranked = [[c for (p, c) in
                                   sorted(zip(test_expprobs[i],
                                              predictor.classes_),
                                          reverse=True)]
                                  for i in range(num_test_points)]
        test_expclasses = [c[0] for c in test_expclasses_ranked]
    else:
        test_expclasses = predictor.predict(test_features)
        test_end_time = timeit.default_timer()

        num_topN = 1
        test_expclasses_ranked = [[c] for c in test_expclasses]

    topN_results = {}
    for n in range(1, num_topN+1):
        misclassified_indexes = [test_indexes[i] for i in
                                 range(num_test_points) if
                                 test_realclasses[i] not in
                                 test_expclasses_ranked[i][:n]]
        topN_results['top{}'.format(n)] = {
            'misclassified_indexes': misclassified_indexes,
            'accuracy': 1 - (len(misclassified_indexes)/num_test_points)
        }

    stats = {
        'confusion_matrix': sklearn.metrics.confusion_matrix(
            test_realclasses, test_expclasses, labels=all_classes
        ),
        'topN_results': topN_results,
        'train_time': train_end_time - start_time,
        'test_time': test_end_time - train_end_time
    }
    if hasattr(predictor, 'n_iter_'):
        stats['iterations'] = predictor.n_iter_
    if normalize_features:
        stats['reduced_variance_ratio'] = \
            np.sum(dim_reducer.explained_variance_ratio_)
    return stats


def crossvalidation_run(predictor_factory, features, point_classes,
                        all_classes, validation_count, mode='features',
                        normalize_features=True):
    num_points = len(point_classes)
    validation_indexes = np.array_split(np.random.permutation(num_points),
                                        validation_count)

    totals = defaultdict(int)
    topN_totals = defaultdict(lambda: {
        'accuracy': 0,
        'misclassified_indexes': set()
    })

    for test_indexes in validation_indexes:
        train_indexes = list(set(range(num_points)).difference(test_indexes))

        if mode == 'dists':
            real_features = features[:, train_indexes]
        else:
            real_features = features

        stats = classification_run(predictor_factory, real_features,
                                   point_classes, all_classes, train_indexes,
                                   test_indexes)

        totals['confusion_matrix'] += stats['confusion_matrix']
        totals['train_time'] += stats['train_time']
        totals['test_time'] += stats['test_time']
        if 'iterations' in stats:
            totals['iterations'] += stats['iterations']
        if 'reduced_variance_ratio' in stats:
            totals['reduced_variance_ratio'] += stats['reduced_variance_ratio']
        for name, results in iteritems(stats['topN_results']):
            topN_totals[name]['accuracy'] += results['accuracy']
            topN_totals[name]['misclassified_indexes'].update(
                results['misclassified_indexes']
            )

    final_stats = {
        'classes': all_classes,
        'confusion_matrix': totals['confusion_matrix'],
        'train_time': totals['train_time'] / validation_count,
        'test_time': totals['test_time'] / validation_count
    }
    if 'iterations' in totals:
        final_stats['average_iterations'] = (
            totals['iterations'] / validation_count
        )
    if 'reduced_variance_ratio' in totals:
        final_stats['average_reduced_variance_ratio'] = (
            totals['reduced_variance_ratio'] / validation_count
        )
    for name, curr_totals in iteritems(topN_totals):
        final_stats[name] = {
            'accuracy': curr_totals['accuracy'] / validation_count,
            'misclassified_indexes': list(curr_totals['misclassified_indexes'])
        }

    return final_stats


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyJSONEncoder, self).default(obj)


def run_classify_step(options, exp_options):
    log = logging.getLogger('modmap.classify')

    if options['classifiers'] == 'all':
        classifier_names = classifiers_by_name.keys()
    else:
        classifier_names = options['classifiers']

    if options['features_type'] == 'mmg-dists':
        features = file_formats.import_dists(options['features_file'])
        features_mode = 'dists'
    elif options['features_type'] == 'mmg-cgrs':
        features = file_formats.import_cgrs(options['features_file'])
        features_mode = 'features'
    elif options['features_type'] == 'json-features':
        with open(options['features_file'], 'r') as infile:
            features = json.load(infile)
        features_mode = 'features'

    with open(options['metadata_file'], 'r') as infile:
        metadata = json.load(infile)
    point_classes = np.array([x['group'] for x in metadata])
    all_classes = sorted(set(x['group'] for x in metadata))

    if options['validation_count'] == 'one-out':
        validation_count = len(metadata)
    else:
        validation_count = options['validation_count']

    if 'skip_normalization' not in options:
        normalize_features = True
    else:
        normalize_features = not options['skip_normalization']

    results = {}
    for i, classifier_name in enumerate(classifier_names):
        with job_utils.log_step(
                 "classifier '{}' ({}/{})".format(classifier_name, i+1,
                                                  len(classifier_names))):
            timeout_seconds = 600  # TODO: make this an options key?
            try:
                with stopit.ThreadingTimeout(seconds=timeout_seconds,
                                             swallow_exc=False):
                    results[classifier_name] = crossvalidation_run(
                        classifiers_by_name[classifier_name], features,
                        point_classes, all_classes, validation_count,
                        mode=features_mode,
                        normalize_features=normalize_features
                    )
            except stopit.TimeoutException:
                log.warning(
                    '*** classifier run timed out after ~%d seconds, skipping',
                    timeout_seconds
                )
            except Exception as e:
                log.warning(
                    "*** classifier run failed with error '%s', skipping", e
                )

    with open(options['output_file'], 'w') as outfile:
        json.dump(results, outfile, cls=NumpyJSONEncoder)
