import os
import time
import io
import Queue

import threading

import celery
from fishface_celery import app as celery_app

from raspi_logging import logger

REAL_HARDWARE = not os.path.isfile('FAKE_THE_HARDWARE')

capture_thread = None
capture_thread_lock = threading.RLock()


class Camera(object):
    def __init__(self, resolution=(2048, 1536), rotation=180):
        self._lock = threading.RLock()

        if REAL_HARDWARE:
            logger.info('Running with real power supply.')
            import picamera
            self.cam_class = picamera.PiCamera
        else:
            logger.warning('Running with fake power supply.')
            import FakeHardware
            self.cam_class = FakeHardware.PiCamera

        self.cam = self.cam_class()
        self.cam.resolution = resolution
        self.cam.rotation = rotation

    def get_image_with_capture_time(self):
        stream = io.BytesIO()
        with self._lock:
            capture_time = float(time.time())
            self.camera.capture(stream, format='jpeg')

        return (stream, capture_time)

camera = Camera()

# Move this into the yet-to-be-implemented scheduler
# camera.open()


def delay_until(unix_timestamp):
    now = time.time()
    while now < unix_timestamp:
        time.sleep(unix_timestamp - now)
        now = time.time()


def delay_for_seconds(seconds):
    later = time.time() + seconds
    delay_until(later)


class ThreadWithHeartbeat(threading.Thread):
    """
    Remember to override the _heartbeat_run(), _pre_run(), and _post_run() methods.
    """

    def __init__(self, heartbeat_interval=0.2, heartbeat_publish_interval=None, *args, **kwargs):
        super(ThreadWithHeartbeat, self).__init__(*args, **kwargs)

        self._name = None

        self._heartbeat_count = 0
        self._heartbeat_timestamp = None
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_log_interval = heartbeat_publish_interval
        self._heartbeat_lock = threading.Lock()

        self._keep_looping = True
        self.ready = False

        logger.debug('{} thread initialized.'.format(self.name))

    def run(self):
        logger.debug('{} thread started.'.format(self.name))
        try:
            self._pre_run()

            while self._keep_looping:
                self._heartbeat_run()
                self.beat_heart()
                delay_for_seconds(self._heartbeat_interval)
        finally:
            self._post_run()

    def set_ready(self):
        logger.info('{} thread reports that it is ready.'.format(self.name))
        self.ready = True

    def _heartbeat_run(self):
        raise NotImplementedError

    def _pre_run(self):
        self.set_ready()

    def _post_run(self):
        pass

    def beat_heart(self):
        with self._heartbeat_lock:
            self._heartbeat_timestamp = time.time()
            self._heartbeat_count += 1

        if self._heartbeat_log_interval is not None:
            if not self._heartbeat_count % self._heartbeat_log_interval:
                logger.debug('{} thread heartbeat count is {}'.format(self.name,
                                                                      self._heartbeat_count))
        self.publish_heartbeat()

    def publish_heartbeat(self):
        with self._heartbeat_lock:
            timestamp, count = self._heartbeat_timestamp, self._heartbeat_count

        celery_app.send_task('results.thread_heartbeat', kwargs={
            'name': self.name,
            'timestamp': timestamp,
            'count': count,
        })

    @property
    def heartbeat_count(self):
        return self._heartbeat_count

    @property
    def last_heartbeat(self):
        return self._heartbeat_timestamp

    @property
    def last_heartbeat_delta(self):
        try:
            return time.time() - self._heartbeat_timestamp
        except TypeError:
            return None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        if self._name is None:
            self._name = new_name + "." + str(time.time())
        else:
            logger.warning("Tried to rename thread.  Thread names are immutable once set.")

    def abort(self, complete=False):
        self._keep_looping = False
        if complete:
            logger.info('Thread {} complete.  Shutting down.'.format(self.name))
        else:
            logger.warning('Thread {} aborted.'.format(self.name))


class CaptureThread(ThreadWithHeartbeat):
    def __init__(self, *args, **kwargs):
        super(CaptureThread, self).__init__(*args, **kwargs)
        self.name = 'capture_thread'

        self.queue = Queue.PriorityQueue()

        self._wait_for_capture_when_less_than = self._heartbeat_interval * 3

        self.cam = Camera()

        self._next_capture_time = None

    def _heartbeat_run(self):
        if self._next_capture_time is None:
            self._next_capture_time = self.pop_next_request()

        if not self._keep_looping:
            return

        if self._next_capture_time - time.time() < self._wait_for_capture_when_less_than:
            delay_until(self._next_capture_time)
            stream, timestamp = self.cam.get_image_with_capture_time()

            image = stream.read()

            celery_app.send_task('results.post_image', kwargs={
                'image': image,
                'requested_timestamp': self._next_capture_time,
                'actual_timestamp': timestamp
            })

            self._next_capture_time = None

    def _pre_run(self):
        self.set_ready()

    def _post_run(self):
        pass

    def push_capture_request(self, requested_capture_timestamp):
        self.queue.put(requested_capture_timestamp)

    def pop_next_request(self):
        try:
            self.queue.get(block=False)
        except Queue.Empty:
            self.abort(complete=True)

    def abort(self, complete=False):
        super(CaptureThread, self).abort(complete=complete)
        self.cam.close()
        self.cam = None



@celery.shared_task(name="camera.push_capture_request")
def queue_capture_request(requested_capture_timestamp):
    global capture_thread, capture_thread_lock
    with capture_thread_lock:
        if capture_thread is None:
            capture_thread = CaptureThread()

    capture_thread.push_capture_request(requested_capture_timestamp)


class PowerSupplyError(Exception):
    pass