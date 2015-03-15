import os
import logging

from util.misc_utilities import return_text_file_contents

APP_ROOT = os.path.expanduser('~')
UTIL_DIR = os.path.join(APP_ROOT, 'FishFace2', 'util')

CAMERA_RESOLUTION = (512, 384)
CAMERA_ROTATION = 180


REAL_CAMERA = not os.path.isfile(os.path.join(UTIL_DIR, 'FAKE_CAMERA'))
if REAL_CAMERA:
    logging.info('Running with real camera.')
    import picamera as camera_module
else:
    logging.warning('Running with fake camera.')
    from ff_celery import FakeHardware as camera_module
CAMERA_CLASS = camera_module.PiCamera


REAL_POWER_SUPPLY = not os.path.isfile(os.path.join(UTIL_DIR, 'FAKE_POWER_SUPPLY'))
if REAL_POWER_SUPPLY:
    logging.info('Running with real power supply.')
    from util.RobustPowerSupply import RobustPowerSupply as PSU_CLASS
else:
    logging.warning('Running with fake power supply.')
    from ff_celery.FakeHardware import HP6652a as PSU_CLASS


redis_password_file_path = os.path.join(APP_ROOT, 'etc', 'redis', 'redis_password')
redis_hostname_file_path = os.path.join(APP_ROOT, 'var', 'run', 'redis.hostname')
REDIS_PASSWORD = return_text_file_contents(redis_password_file_path)
REDIS_HOSTNAME = return_text_file_contents(redis_hostname_file_path)

CELERY_BROKER_URL = (('redis://' + ':' + str(REDIS_PASSWORD) + '@' if REDIS_PASSWORD else '') +
                     REDIS_HOSTNAME)

CELERY_RESULT_URL = CELERY_BROKER_URL

CELERY_QUEUE_NAMES = ['drone', 'django', 'learn', 'cjc', 'results']


ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1 = 2
ML_RESERVE_DATA_FRACTION_FOR_VERIFICATION = 0.1
ML_STAGE_1_IMAGES_PER_CHUNK = 25

CJR_CREATION_TIMEOUT = 30
CAMERA_QUEUE_PRELOAD = 15