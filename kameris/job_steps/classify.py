from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
import json
import logging
import kameris_formats
import numpy as np
import os
import scipy.sparse as sparse
from six import iteritems
from six.moves import range, zip
import stopit
import timeit

import sklearn
from sklearn.decomposition import TruncatedSVD
from sklearn.externals import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ._classifiers import classifiers_by_name
from ..utils import job_utils


def avg_num_nonzero_entries(features):
    return int(sum(np.count_nonzero(f) for f in features) / len(features))


def build_pipeline(classifier_factory, num_features, options):
    normalize_features = not options.get('skip_normalization', False)
    dim_reduce_fraction = options.get('dim_reduce_fraction', 0.1)

    # setup normalizers if needed
    normalizers = []
    if normalize_features:
        # scale each feature dimension to unit variance
        # note mean scaling won't work with sparse vectors
        # it seems obvious to move this after the SVD but that reduces
        #   classifier performance substantially
        normalizers.append(('scaler', StandardScaler(with_mean=False)))

        # reduce dimensionality to some fraction of its original
        normalizers.append(
            ('dim_reducer',
             TruncatedSVD(n_components=int(
                np.ceil(num_features * dim_reduce_fraction)
             )))
        )

    return Pipeline(normalizers + [('classifier', classifier_factory())])


def classification_run(classifier_factory, features, point_classes,
                       unique_classes, train_indexes, test_indexes, options):
    num_test_points = len(test_indexes)
    train_classes = point_classes[train_indexes]
    test_realclasses = point_classes[test_indexes]

    # split training and testing feature vectors
    train_features = [features[i] for i in train_indexes]
    test_features = [features[i] for i in test_indexes]
    if sparse.issparse(train_features[0]):
        train_features = sparse.vstack(train_features, format='csr')
        test_features = sparse.vstack(test_features, format='csr')

    # train model
    pipeline = build_pipeline(classifier_factory,
                              avg_num_nonzero_entries(features), options)
    start_time = timeit.default_timer()
    pipeline.fit(train_features, train_classes)
    train_end_time = timeit.default_timer()

    # run predictions and compute rankings
    if hasattr(pipeline, 'predict_proba'):
        test_expprobs = pipeline.predict_proba(test_features)
        test_end_time = timeit.default_timer()

        num_topN = len(pipeline.classes_) - 1
        test_expclasses_ranked = [[c for (p, c) in
                                   sorted(zip(test_expprobs[i],
                                              pipeline.classes_),
                                          reverse=True)]
                                  for i in range(num_test_points)]
        test_expclasses = [c[0] for c in test_expclasses_ranked]
    else:
        test_expclasses = pipeline.predict(test_features)
        test_end_time = timeit.default_timer()

        num_topN = 1
        test_expclasses_ranked = [[c] for c in test_expclasses]

    # separate top-N results
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

    # compute and return stats
    stats = {
        'confusion_matrix': sklearn.metrics.confusion_matrix(
            test_realclasses, test_expclasses, labels=unique_classes
        ),
        'topN_results': topN_results,
        'train_time': train_end_time - start_time,
        'test_time': test_end_time - train_end_time
    }
    if hasattr(pipeline, 'n_iter_'):
        stats['iterations'] = pipeline.n_iter_
    if 'dim_reducer' in pipeline.named_steps:
        stats['reduced_variance_ratio'] = np.sum(
            pipeline.named_steps['dim_reducer'].explained_variance_ratio_
        )
    return stats


def crossvalidation_run(classifier_factory, features, features_mode,
                        point_classes, unique_classes, options):
    # perform validation group splitting
    validation_count = options['validation_count']
    num_points = len(point_classes)
    if 'validation_split_classes' in options:
        val_all_classes = options['validation_split_classes']
        val_split_classes = np.array_split(
            np.random.permutation(np.unique(val_all_classes)), validation_count
        )
        validation_indexes = [
            np.concatenate([np.where(val_all_classes == split_class)[0]
                            for split_class in split_classes])
            for split_classes in val_split_classes
        ]
    else:
        validation_indexes = np.array_split(np.random.permutation(num_points),
                                            validation_count)

    # setup storage for accuracy/stats
    totals = defaultdict(int)
    topN_totals = defaultdict(lambda: {
        'accuracy': 0,
        'misclassified_indexes': set()
    })

    # train classifier and update stats
    for test_indexes in validation_indexes:
        train_indexes = list(set(range(num_points)).difference(test_indexes))

        if features_mode == 'dists':
            real_features = features[:, train_indexes]
        else:
            real_features = features

        stats = classification_run(
            classifier_factory, real_features, point_classes, unique_classes,
            train_indexes, test_indexes, options
        )

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

    # compute and return summary stats
    final_stats = {
        'classes': unique_classes,
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
    log = logging.getLogger('kameris.classify')
    classifier_names = options['classifiers']
    save_model = options.get('save_model', True)

    # import features
    features_filename = options['features_file']
    if features_filename.endswith('.mm-dist'):
        features = kameris_formats.dist_reader \
                                  .read_matrix(options['features_file'])
        features_mode = 'dists'
    elif features_filename.endswith('.mm-repr'):
        features = []
        reader = kameris_formats.repr_reader(options['features_file'])
        for i in range(reader.count):
            features.append(reader.read_matrix(i, flatten=True))

        features_mode = 'features'
    else:
        raise Exception("Unknown type for file '{}'".format(features_filename))

    # load classes from metadata
    with open(options['metadata_file'], 'r') as infile:
        metadata = json.load(infile)
    point_classes = np.array([x['group'] for x in metadata])
    unique_classes = np.unique(point_classes)
    if 'validation_split_by' in options:
        options['validation_split_classes'] = np.array([
            x[options['validation_split_by']] for x in metadata
        ])

    # run classifiers and obtain results
    results = {}
    for i, classifier_name in enumerate(classifier_names):
        with job_utils.log_step(
                 "classifier '{}' ({}/{})".format(classifier_name, i+1,
                                                  len(classifier_names))):
            timeout = options.get('timeout', 600)
            try:
                with stopit.ThreadingTimeout(seconds=timeout,
                                             swallow_exc=False):
                    classifier_factory = classifiers_by_name[classifier_name]

                    # compute cross-validation results
                    results[classifier_name] = crossvalidation_run(
                        classifier_factory, features, features_mode,
                        point_classes, unique_classes, options
                    )

                    # save the model file
                    if 'generation_options' in options and save_model:
                        # train the model
                        pipeline = build_pipeline(
                            classifier_factory,
                            avg_num_nonzero_entries(features), options
                        )
                        pipeline.fit(features, point_classes)

                        # save the model
                        model_data = {
                            'sklearn_version': sklearn.__version__,
                            'generation_options':
                                options['generation_options'],
                            'predictor': pipeline
                        }
                        model_file = os.path.join(
                            os.path.dirname(options['output_file']),
                            '{}_{}.mm-model'.format(
                                os.path.splitext(
                                    os.path.basename(options['output_file'])
                                )[0],
                                classifier_name
                            )
                        )
                        joblib.dump(model_data, model_file)
            except stopit.TimeoutException:
                log.warning(
                    '*** classifier run timed out after ~%d seconds, skipping',
                    timeout
                )
            except Exception as e:
                log.warning(
                    "*** classifier run failed with error '%s', skipping", e
                )

    # write results
    with open(options['output_file'], 'w') as outfile:
        json.dump(results, outfile, cls=NumpyJSONEncoder)
