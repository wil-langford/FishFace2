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

        self.close_if_greater_than = 30
        self.open_if_less_than = 4

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


@celery.shared_task(name="psu.post_image")
def post_image(meta):
    pass


class PowerSupplyError(Exception):
    pass