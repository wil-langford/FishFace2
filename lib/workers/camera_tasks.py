import time
import io
import Queue
import threading

import celery
import celery.exceptions

from lib.fishface_celery import celery_app
from lib.fishface_logging import logger

from lib.misc_utilities import delay_until

import etc.fishface_config as ff_conf

capture_thread = None
capture_thread_lock = threading.RLock()

import lib.thread_with_heartbeat as thread_with_heartbeat


@celery.shared_task(name='camera.ping')
def ping():
    return True


@celery.shared_task(bind=True, name='camera.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


class Camera(object):
    def __init__(self, resolution=ff_conf.CAMERA_RESOLUTION, rotation=ff_conf.CAMERA_ROTATION):
        self._lock = threading.RLock()

        self.cam = None

        self.cam_class = ff_conf.camera_class
        self.resolution = resolution
        self.rotation = rotation

        self.open()

    def get_image_with_capture_time(self):
        stream = io.BytesIO()
        with self._lock:
            capture_time = float(time.time())
            self.cam.capture(stream, format='jpeg')

        return (stream.read(), capture_time)

    def close(self):
        self.cam.close()
        self.cam = None

    def open(self):
        self.cam = self.cam_class()
        self.cam.resolution = self.resolution
        self.cam.rotation = self.rotation


class CaptureThread(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, *args, **kwargs):
        super(CaptureThread, self).__init__(*args, **kwargs)
        self.name = 'capture_thread'

        self.queue = Queue.PriorityQueue()

        self._wait_for_capture_when_less_than = self._heartbeat_interval * 3

        self.cam = Camera()

        self._next_capture_time = None
        self._next_capture_meta = None

        self._thread_started_at = time.time()

    def _heartbeat_run(self):
        if self._next_capture_time is None:
            print 'Popping next.'
            self._next_capture_time, self._next_capture_meta = self.pop_next_request()
            if self._next_capture_meta is None:
                if self.thread_age > 3:
                    self.abort(complete=True)
                return

        print self._next_capture_time
        print self._next_capture_meta

        if not self._keep_looping:
            print 'returning early'
            return

        if self._next_capture_time - time.time() < self._wait_for_capture_when_less_than:
            delay_until(self._next_capture_time)
            image, timestamp = self.cam.get_image_with_capture_time()

            print "image created with size [{}]".format(len(image))

            meta = self._next_capture_meta
            meta['capture_timestamp'] = timestamp

            print "meta updated"

            r = celery_app.send_task('results.post_image',
                                     kwargs={'image_data': image, 'meta': meta})

            print "post post"

            self.queue.task_done()

            self._next_capture_time = None
            self._next_capture_meta = None

    def _pre_run(self):
        self.set_ready()

    def _post_run(self):
        pass

    def push_capture_request(self, requested_capture):
        self.queue.put(requested_capture)

    def pop_next_request(self):
        try:
            return self.queue.get_nowait()
        except Queue.Empty:
            return (None, None)

    def abort(self, complete=False):
        print "aborting thread.  complete? {}".format(complete)
        # we don't want to accept any more imagery requests after we start the abort
        self.push_capture_request = lambda x: True

        super(CaptureThread, self).abort(complete=complete)
        if not complete:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Queue.Empty:
                    continue
                self.queue.task_done()

        self.cam.close()
        self.cam = None


@celery.shared_task(name="camera.queue_capture_request")
def queue_capture_request(requested_capture_timestamp, meta):
    print requested_capture_timestamp, meta
    global capture_thread, capture_thread_lock
    with capture_thread_lock:
        if capture_thread is None or not capture_thread.is_alive():
            startup_event = threading.Event()
            capture_thread = CaptureThread(
                startup_event=startup_event,
                heartbeat_interval=0.2
            )
            capture_thread.start()
            if not startup_event.wait(timeout=6):
                logger.error("Couldn't create capture thread.")

    if capture_thread is not None and capture_thread.ready:
        capture_thread.push_capture_request((requested_capture_timestamp, meta))
    else:
        logger.error("Tried to push request, but capture thread not ready.")

    return requested_capture_timestamp, meta


@celery.shared_task(name='camera.start_capture_thread')
def start_capture_thread():
    global capture_thread, capture_thread_lock
    if capture_thread is not None:
        return True

    with capture_thread_lock:
        capture_thread = CaptureThread(startup_event=threading.Event())

    capture_thread.start()
    try:
        capture_thread.ready_event.wait(timeout=5)
        return True
    except celery.exceptions.TimeoutError:
        return False


@celery.shared_task(name='camera.stop_capture_thread')
def stop_capture_thread(force=False):
    global capture_thread, capture_thread_lock
    if capture_thread is None:
        return True

    if force or capture_thread.queue.empty():
        capture_thread.abort()

    for i in range(5):
        time.sleep(0.5)
        if capture_thread is None:
            return True

    return False


@celery.shared_task(name='camera.abort')
def abort():
    stop_capture_thread(force=True)


class CameraError(Exception):
    pass