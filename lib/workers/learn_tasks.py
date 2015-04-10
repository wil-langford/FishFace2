import sklearn.preprocessing as skp
import sklearn.cluster as skc
import celery
from lib.fishface_celery import celery_app

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
def create_estimator(hu_moments, n_clusters=80, n_init=10, init='k-means++'):
    try:
        if len(hu_moments[0]) != 7:
            raise ClusteringError("Hu moments contain 7 elements - the passed object doesn't fit" +
                                  "that criteria.")
    except IndexError:
        raise ClusteringError("Could not index to the 0th element of passed hu_moments.  " +
                              "Is it iterable?")

    data = skp.scale(hu_moments)
    estimator = skc.KMeans(init=init, n_clusters=n_clusters, n_init=n_init)

    estimator.fit(data)

    return estimator


class ClusteringError(Exception):
    pass