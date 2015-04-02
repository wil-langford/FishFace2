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

import lib.thread_with_heartbeat as thread_with_heartbeat

if ff_conf.REAL_CAMERA:
    logger.info('Running with real camera.')
    from picamera import PiCamera as camera_class
else:
    logger.warning('Running with fake camera.')
    from lib.FakeHardware import PiCamera as camera_class

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

        self.cam_class = camera_class
        self.resolution = resolution
        self.rotation = rotation

        self.open()

    def get_image_with_capture_time(self):
        stream = io.BytesIO()
        with self._lock:
            capture_time = float(time.time())
            self.cam.capture(stream, format='jpeg')

        stream.seek(0)

        return (stream.read(), capture_time)

    def close(self):
        self.cam.close()
        self.cam = None

    def open(self):
        self.cam = self.cam_class()
        self.cam.resolution = self.resolution
        self.cam.rotation = self.rotation

        for settings_group in ff_conf.CAMERA_CONSISTENCY_SETTINGS:
            for key, value in settings_group.iteritems():
                try:
                    setattr(self.cam, key, value)
                except AttributeError:
                    logger.error("Can't set attribute/property {} on camera object.".format(key))


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
            self._next_capture_time, self._next_capture_meta = self.pop_next_request()
            if self._next_capture_meta is None:
                if self.thread_age > 3:
                    self.abort(complete=True)
                return

        if not self._keep_looping:
            return

        if self._next_capture_time - time.time() < self._wait_for_capture_when_less_than:
            delay_until(self._next_capture_time)
            image, timestamp = self.cam.get_image_with_capture_time()

            meta = self._next_capture_meta
            meta['capture_timestamp'] = timestamp
            meta['requested_timestamp'] = self._next_capture_time
            meta['delta'] = timestamp - self._next_capture_time

            r = celery_app.send_task('results.post_image',
                                     kwargs={'image_data': image, 'meta': meta})

            self.queue.task_done()

            self._next_capture_time = None
            self._next_capture_meta = None

            return {'image_post_task_id': r.id}

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

        try:
            self.cam.close()
            self.cam = None
        except AttributeError:
            pass


class CaptureThreadTask(celery.Task):
    abstract = True
    _capture_thread = {'thread': None}
    _capture_thread_lock = threading.Lock()

    @property
    def capture_thread(self):
        if self.extant:
            return self._capture_thread['thread']
        else:
            with self._capture_thread_lock:
                self._capture_thread['thread'] = CaptureThread(
                    heartbeat_interval=0.2,
                    startup_event=threading.Event()
                )

            self._capture_thread['thread'].start()

            try:
                self._capture_thread['thread'].ready_event.wait(timeout=5)
                return self._capture_thread['thread']
            except celery.exceptions.TimeoutError:
                raise CaptureThreadError("Could not start capture thread.")

    @property
    def extant(self):
        return (self._capture_thread['thread'] is not None
                and self._capture_thread['thread'].is_alive())


@celery.shared_task(base=CaptureThreadTask, name='camera.queue_capture_request')
def queue_capture_request(requested_capture_timestamp, meta):
    queue_capture_request.capture_thread.push_capture_request((requested_capture_timestamp, meta))

    return requested_capture_timestamp, meta


@celery.shared_task(base=CaptureThreadTask, name='camera.abort')
def abort():
    if abort.extant:
        abort.capture_thread.abort()
        return True
    return False


class CameraError(Exception):
    pass


class CaptureThreadError(Exception):
    pass