from __future__ import absolute_import, division, unicode_literals

from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.neighbors.nearest_centroid import NearestCentroid
from sklearn.svm import SVC

from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.discriminant_analysis import (
    LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis)

from sklearn.neural_network import MLPClassifier

import sklearn.metrics

from collections import defaultdict
import json
import logging
import numpy as np
from six import iteritems
from six.moves import range
import stopit
import timeit

from . import file_formats
from . import utils


def classification_run(predictor_factory, features, point_classes,
                       train_indexes, test_indexes):
    num_test_points = len(test_indexes)
    train_dists = features[train_indexes, :]
    train_classes = point_classes[train_indexes]
    test_dists = features[test_indexes, :]
    test_realclasses = point_classes[test_indexes]

    predictor = predictor_factory()
    start_time = timeit.default_timer()
    predictor.fit(train_dists, train_classes)
    train_end_time = timeit.default_timer()

    if hasattr(predictor, 'predict_proba'):
        test_expprobs = predictor.predict_proba(test_dists)
        test_end_time = timeit.default_timer()

        num_topN = len(predictor.classes_) - 1
        test_expclasses_ranked = [[c for (p, c) in
                                   sorted(zip(test_expprobs[i],
                                              predictor.classes_),
                                          reverse=True)]
                                  for i in range(num_test_points)]
        test_expclasses = [c[0] for c in test_expclasses_ranked]
    else:
        test_expclasses = predictor.predict(test_dists)
        test_end_time = timeit.default_timer()

        num_topN = 1
        test_expclasses_ranked = [[c] for c in test_expclasses]

    topN_results = {}
    for n in range(1, num_topN+1):
        misclassified_indexes = [i for i in range(num_test_points) if
                                 test_realclasses[i] not in
                                 test_expclasses_ranked[i][:n]]
        topN_results['top{}'.format(n)] = {
            'misclassified_indexes': misclassified_indexes,
            'accuracy': 1 - (len(misclassified_indexes)/num_test_points)
        }

    stats = {
        'classes': predictor.classes_,
        'confusion_matrix': sklearn.metrics.confusion_matrix(test_realclasses,
                                                             test_expclasses),
        'topN_results': topN_results,
        'train_time': train_end_time - start_time,
        'test_time': test_end_time - train_end_time
    }
    if hasattr(predictor, 'n_iter_'):
        stats['iterations'] = predictor.n_iter_
    return stats


def crossvalidation_run(predictor_factory, features, point_classes,
                        validation_count, mode='features'):
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
                                   point_classes, train_indexes, test_indexes)

        totals['classes'] = stats['classes']
        totals['confusion_matrix'] += stats['confusion_matrix']
        totals['train_time'] += stats['train_time']
        totals['test_time'] += stats['test_time']
        if 'iterations' in stats:
            totals['iterations'] += stats['iterations']
        for name, results in iteritems(stats['topN_results']):
            topN_totals[name]['accuracy'] += results['accuracy']
            topN_totals[name]['misclassified_indexes'].update(
                results['misclassified_indexes']
            )

    final_stats = {
        'classes': totals['classes'],
        'confusion_matrix': totals['confusion_matrix'],
        'train_time': totals['train_time'] / validation_count,
        'test_time': totals['test_time'] / validation_count
    }
    if 'iterations' in totals:
        final_stats['average_iterations'] = (
            totals['iterations'] / validation_count
        )
    for name, curr_totals in iteritems(topN_totals):
        final_stats[name] = {
            'accuracy': curr_totals['accuracy'] / validation_count,
            'misclassified_indexes': list(curr_totals['misclassified_indexes'])
        }

    return final_stats


classifiers = {
    '10-nearest-neighbors': lambda: KNeighborsClassifier(n_neighbors=10),
    'nearest-centroid-mean': lambda: NearestCentroid(metric='euclidean'),
    'nearest-centroid-median': lambda: NearestCentroid(metric='manhattan'),
    'logistic-regression': lambda: LogisticRegression(),
    'sgd': lambda: SGDClassifier(),
    'linear-svm': lambda: SVC(kernel='linear', C=0.025),
    'quadratic-svm': lambda: SVC(kernel='poly', degree=2, C=0.025),
    'rbf-svm': lambda: SVC(C=0.025),
    'gaussian-process': lambda: GaussianProcessClassifier(),
    'decision-tree': lambda: DecisionTreeClassifier(),
    'random-forest': lambda: RandomForestClassifier(),
    'adaboost': lambda: AdaBoostClassifier(),
    'gaussian-naive-bayes': lambda: GaussianNB(),
    'multinomial-naive-bayes': lambda: MultinomialNB(),
    'lda': lambda: LinearDiscriminantAnalysis(),
    'qda': lambda: QuadraticDiscriminantAnalysis(),
    'neural-network': lambda: MLPClassifier()
}


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


def run_experiment(options):
    log = logging.getLogger('modmap.classify')

    if options['classifiers'] == 'all':
        classifier_names = classifiers.keys()
    else:
        classifier_names = options['classifiers']

    if options['features_type'] == 'mmg-dists':
        features = file_formats.import_dists(options['features_file'])
        features_mode = 'dists'
    elif options['features_type'] == 'mmg-repr':
        features = file_formats.import_repr(options['features_file'])
        features_mode = 'features'
    elif options['features_type'] == 'json-features':
        with open(options['features_file'], 'r') as infile:
            features = json.load(infile)
        features_mode = 'features'

    with open(options['metadata_file'], 'r') as infile:
        metadata = json.load(infile)
        point_classes = np.array([x['group'] for x in metadata])

    if options['validation_count'] == 'one-out':
        validation_count = len(metadata)
    else:
        validation_count = options['validation_count']

    results = {}
    for i, classifier_name in enumerate(classifier_names):
        with utils.log_step(
                 "classifier '{}' ({}/{})".format(classifier_name, i+1,
                                                  len(classifier_names))):
            timeout_seconds = 600  # TODO: make this an options key?
            try:
                with stopit.ThreadingTimeout(seconds=timeout_seconds,
                                             swallow_exc=False):
                    results[classifier_name] = crossvalidation_run(
                        classifiers[classifier_name], features, point_classes,
                        validation_count, mode=features_mode
                    )
            except stopit.TimeoutException:
                log.warning(
                    "*** classifier run timed out after ~{} seconds, skipping"
                    .format(timeout_seconds)
                )
            except Exception as e:
                log.warning(
                    "*** classifier run failed with error '{}', skipping"
                    .format(e)
                )

    with open(options['output_file'], 'w') as outfile:
        json.dump(results, outfile, cls=NumpyJSONEncoder)
