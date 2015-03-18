from __future__ import print_function

import sys
import os
from os.path import join as path_join

import logging
import numpy as np

from lib.misc_utilities import return_text_file_contents, is_file

HOME = os.path.expanduser('~')
VENV = path_join(HOME, 'venvs', 'FishFace2.venv')
LOG_LEVEL = 'INFO'

try:
    ROOT = os.environ['FF_ROOT']
except KeyError:
    ROOT = path_join(os.path.expanduser('~'), 'FishFace2')

ETC = path_join(ROOT, 'etc')
VAR = path_join(ROOT, 'var')
VAR_RUN = path_join(VAR, 'run')
VAR_LOG = path_join(VAR, 'log')
LIB = path_join(ROOT, 'lib')
BIN = path_join(ROOT, 'bin')


DJANGO_DIR = path_join(LIB, 'django')

CAMERA_RESOLUTION = (512, 384)
CAMERA_ROTATION = 180

NORMALIZED_SHAPE = (384, 512)
NORMALIZED_DTYPE = np.uint8

REAL_CAMERA = not is_file(ETC, 'FAKE_CAMERA')
if REAL_CAMERA:
    logging.info('Running with real camera.')
    from picamera import PiCamera as camera_class
else:
    logging.warning('Running with fake camera.')
    from lib.FakeHardware import PiCamera as camera_class

REAL_POWER_SUPPLY = not is_file(ETC, 'FAKE_POWER_SUPPLY')
if REAL_POWER_SUPPLY:
    logging.info('Running with real power supply.')
    from lib.RobustPowerSupply import RobustPowerSupply as psu_class
else:
    logging.warning('Running with fake power supply.')
    from lib.FakeHardware import HP6652a as psu_class


redis_password_file_path = path_join(ETC, 'redis', 'redis_password')
redis_hostname_file_path = path_join(VAR_RUN, 'redis.hostname')
REDIS_PASSWORD = str(return_text_file_contents(redis_password_file_path))
REDIS_HOSTNAME = str(return_text_file_contents(redis_hostname_file_path))

CELERY_BROKER_URL = 'redis://' + ((':' + REDIS_PASSWORD + '@') if REDIS_PASSWORD else '')
CELERY_BROKER_URL += REDIS_HOSTNAME

CELERY_RESULT_URL = CELERY_BROKER_URL

CELERY_QUEUE_NAMES = ['drone', 'django', 'learn', 'cjc', 'results', 'psu', 'camera']


ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1 = 2
ML_RESERVE_DATA_FRACTION_FOR_VERIFICATION = 0.1
ML_STAGE_1_IMAGES_PER_CHUNK = 25

CJR_CREATION_TIMEOUT = 30
CAMERA_QUEUE_PRELOAD = 15


def bash_exports():
    return 'export ' + ' '.join(['FF_{export_me}={value}'.format(export_me=export_me,
                                                                   value=globals()[export_me])
        for export_me in 'ROOT ETC VAR VAR_RUN VAR_LOG LIB BIN VENV LOG_LEVEL'.split(' ')])


def main():
    if sys.argv[1] == '--exports':
        print(bash_exports())

if __name__ == '__main__':
    main()