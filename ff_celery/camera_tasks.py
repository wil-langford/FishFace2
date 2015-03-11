import os
import time
import io
import Queue
import threading

import celery

from fishface_celery import celery_app
from util.fishface_logging import logger


REAL_HARDWARE = not os.path.isfile('FAKE_THE_HARDWARE')

capture_thread = None
capture_thread_lock = threading.RLock()

import util.thread_with_heartbeat as thread_with_heartbeat


class Camera(object):
    def __init__(self, resolution=(2048, 1536), rotation=180):
        self._lock = threading.RLock()

        if REAL_HARDWARE:
            logger.info('Running with real power supply.')
            import picamera
            self.cam_class = picamera.PiCamera
        else:
            logger.warning('Running with fake power supply.')
            from ff_celery import FakeHardware

            self.cam_class = FakeHardware.PiCamera

        self.cam = self.cam_class()
        self.cam.resolution = resolution
        self.cam.rotation = rotation

    def get_image_with_capture_time(self):
        stream = io.BytesIO()
        with self._lock:
            capture_time = float(time.time())
            self.cam.capture(stream, format_='jpeg')

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


class CaptureThread(thread_with_heartbeat.ThreadWithHeartbeat):
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

            celery_app.send_task('django.post_image', kwargs={
                'image': image,
                'requested_timestamp': self._next_capture_time,
                'actual_timestamp': timestamp
            })

            self.queue.task_done()

            self._next_capture_time = None

    def _pre_run(self):
        self.set_ready()

    def _post_run(self):
        pass

    def push_capture_request(self, requested_capture_timestamp):
        self.queue.put(requested_capture_timestamp)

    def pop_next_request(self):
        try:
            return self.queue.get_nowait()
        except Queue.Empty:
            self.abort(complete=True)

    def abort(self, complete=False):
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


@celery.shared_task(name="camera.push_capture_request")
def queue_capture_request(requested_capture_timestamp):
    global capture_thread, capture_thread_lock
    with capture_thread_lock:
        if capture_thread is None:
            startup_event = threading.Event()
            capture_thread = CaptureThread(startup_event=startup_event)
            if not startup_event.wait(timeout=3):
                logger.error("Couldn't create capture thread.")

    if capture_thread is not None and capture_thread.ready:
        capture_thread.push_capture_request(requested_capture_timestamp)
    else:
        logger.error("Tried to push request, but capture thread not ready.")


class CameraError(Exception):
    pass