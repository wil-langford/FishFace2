import os
import logging

from util.misc_utilities import return_text_file_contents

APP_ROOT = os.path.expanduser('~')

CAMERA_RESOLUTION = (512, 384)
CAMERA_ROTATION = 180


if os.path.isfile('ENABLE_CAMERA'):
    REAL_CAMERA = not os.path.isfile('FAKE_CAMERA')
    if REAL_CAMERA:
        logging.info('Running with real camera.')
        import picamera as camera_module
    else:
        logging.warning('Running with fake camera.')
        from util import FakeHardware as camera_module
    CAMERA_CLASS = camera_module.PiCamera
else:
    CAMERA_CLASS = None


if os.path.isfile('ENABLE_PSU'):
    REAL_POWER_SUPPLY = not os.path.isfile('FAKE_POWER_SUPPLY')
    if REAL_POWER_SUPPLY:
        logging.info('Running with real power supply.')
        from util.RobustPowerSupply import RobustPowerSupply as PSU_CLASS
    else:
        logging.warning('Running with fake power supply.')
        from util.FakeHardware import HP6652a as PSU_CLASS
else:
    PSU_CLASS = None


redis_password_file_path = os.path.join(APP_ROOT, 'etc', 'redis', 'redis_password')
redis_hostname_file_path = os.path.join(APP_ROOT, 'var', 'run', 'redis.hostname')
REDIS_PASSWORD = return_text_file_contents(redis_password_file_path)
REDIS_HOSTNAME = return_text_file_contents(redis_hostname_file_path)


CELERY_BROKER_URL = ('redis://' +
    ':' + str(REDIS_PASSWORD)
        if REDIS_PASSWORD
        else '' +
    '@'
        if (REDIS_HOSTNAME and REDIS_PASSWORD)
        else '' +
    str(REDIS_HOSTNAME)
        if REDIS_HOSTNAME
        else ''
)

CELERY_RESULT_URL = CELERY_BROKER_URL

CELERY_QUEUE_NAMES = ['drone', 'django', 'learn', 'cjc', 'results']


ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1 = 2
ML_RESERVE_DATA_FRACTION_FOR_VERIFICATION = 0.1