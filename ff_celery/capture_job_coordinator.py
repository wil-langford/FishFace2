import celery

from util import thread_with_heartbeat
from ff_celery.fishface_celery import celery_app

thread_registry = thread_with_heartbeat.ThreadRegistry()


@celery.shared_task(bind=True, name='cjc.debug_task')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@celery.shared_task(name='cjc.thread_heartbeat')
def thread_heartbeat(*args, **kwargs):
    global thread_registry
    thread_registry.receive_heartbeat(*args, **kwargs)


class CaptureJobController(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self):
        super(CaptureJobController, self).__init__()

