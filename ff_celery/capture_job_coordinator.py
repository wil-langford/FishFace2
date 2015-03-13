import celery
import redis
import Queue

from util import thread_with_heartbeat
from ff_celery.fishface_celery import celery_app

import util.fishface_config as ff_conf

thread_registry = thread_with_heartbeat.ThreadRegistry()

cjc = None
redis_client = redis.Redis(
    host=ff_conf.REDIS_HOSTNAME,
    password=ff_conf.REDIS_PASSWORD
)


@celery.shared_task(bind=True, name='cjc.debug_task')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@celery.shared_task(name='cjc.thread_heartbeat')
def thread_heartbeat(*args, **kwargs):
    global thread_registry
    thread_registry.receive_heartbeat(*args, **kwargs)


@celery.shared_task(name='cjc.queues_length')
def queues_length(queue_list=None):
    global redis_client
    if queue_list is None:
        queue_list = ff_conf.CELERY_QUEUE_NAMES
    elif isinstance(queue_list, basestring):
        queue_list = [queue_list]

    return [(queue_name, redis_client.llen(queue_name)) for queue_name in queue_list]


class CaptureJobController(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self):
        super(CaptureJobController, self).__init__()

        self.master_queue = Queue.Queue()



if __name__ == '__main__':
    global cjc
    cjc = CaptureJobController()
    cjc.start()