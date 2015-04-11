import sklearn.preprocessing as skp
import sklearn.cluster as skc
import cv2
import numpy as np
import celery
from lib.fishface_celery import celery_app
import collections

import etc.fishface_config as ff_conf
from lib.misc_utilities import n_chunkify

@celery.shared_task(bind=True, name='learn.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


@celery.shared_task(name="learn.create_estimator")
def create_estimator(ted, n_clusters=80, n_init=10,
                                  init='random', max_iter=1000):

    hu_moments, deltas = zip(*[(datum['hu_moments'], datum['delta']) for datum in ted])

    scaler = skp.StandardScaler()
    scaled_data = scaler.fit_transform(hu_moments)
    estimator = skc.KMeans(init=init, n_clusters=n_clusters, n_init=n_init,
                           max_iter=max_iter)
    labels = estimator.fit_predict(scaled_data)

    agg = collections.defaultdict(list)

    for label, delta in zip(labels, deltas):
        agg[label].append(delta)

    label_deltas = dict()

    for key, delta_list in agg.iteritems():
        label_deltas[key] = float(sum(delta_list)) / len(delta_list)

    return {
        'estimator': estimator,
        'scaler': scaler,
        'label_deltas': label_deltas
    }


class ClusteringError(Exception):
    pass