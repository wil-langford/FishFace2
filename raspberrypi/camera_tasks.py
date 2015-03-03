import os
import time

import threading

import celery
from fishface_celery import app as celery_app

from raspi_logging import logger

REAL_HARDWARE = not os.path.isfile('FAKE_THE_HARDWARE')


class Camera(object):
    def __init__(self, real=True, resolution=(2048, 1536), rotation=180):
        self._lock = threading.RLock()
        self.cam = None

        self.resolution = resolution
        self.rotation = rotation

        if REAL_HARDWARE:
            logger.info('Running with real power supply.')
            import picamera
            self.cam_class = picamera.PiCamera
        else:
            logger.warning('Running with fake power supply.')
            import FakeHardware
            self.cam_class = FakeHardware.PiCamera

    def open(self):
        if self.cam is not None:
            return False

        self.cam = self.cam_class()
        self.cam.resolution = self.resolution
        self.cam.rotation = self.rotation

        return True

    def close(self):
        if self.cam is None:
            return False

        self.cam = None

        return True

camera = Camera(real=REAL_HARDWARE)

# Move this into the yet-to-be-implemented scheduler
# camera.open()

class CaptureThreadWithHeartbeat(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(CaptureThread, self).__init__(*args, **kwargs)

        self.close_if_greater_than = 30
        self.open_if_less_than = 4

        self._heartbeat_count = 0
        self._heartbeat_timestamp = None
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_publish_interval = heartbeat_publish_interval
        self._heartbeat_lock = threading.Lock()

        self._keep_looping = True
        self.ready = False

        self._thread_registry = thread_registry

        self._last_known_registry_index = len(self._thread_registry)
        thread_registry.append(self)

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

        if self._heartbeat_publish_interval is not None:
            if not self._heartbeat_count % self._heartbeat_publish_interval:
                logger.debug('{} thread heartbeat count is {}'.format(self.name,
                                                                      self._heartbeat_count))

    @property
    def heartbeat_count(self):
        return self._heartbeat_count

    def _set_name(self, new_name):
        new_name_str = str(new_name)
        logger.info("Renaming thread '{}' to '{}'.".format(self.name, new_name_str))
        self.name = new_name_str

    @property
    def last_heartbeat(self):
        return self._heartbeat_timestamp

    @property
    def last_heartbeat_delta(self):
        if self._heartbeat_timestamp is not None:
            return time.time() - self._heartbeat_timestamp
        else:
            return 1000000

    @property
    def index_in_registry(self):
        if self._thread_registry[self._last_known_registry_index] is self:
            return self._last_known_registry_index

        if self._thread_registry is None:
            return None

        for idx, thr in self._thread_registry:
            if thr is self:
                return idx

        raise Exception("Thread named {} is not in the registry.".format(self.name))

    def abort(self):
        self._keep_looping = False
        logger.info('Thread {} aborted.'.format(self.name))



@celery.shared_task(name="psu.post_image")
def post_image(meta):
    pass


class PowerSupplyError(Exception):
    pass