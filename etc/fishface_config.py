from __future__ import print_function

import sys
import os
from os.path import join as path_join
import fractions

import logging
import numpy as np

from lib.misc_utilities import return_text_file_contents, is_file

HOME = os.path.expanduser('~')
VENV = path_join(HOME, 'venvs', 'FishFace2.venv')
LOG_LEVEL = 'INFO'

OVERALL_LOG_LEVEL = logging.DEBUG
FILE_LOG_LEVEL = logging.DEBUG
LOG_TO_CONSOLE = False
CONSOLE_LOG_LEVEL = logging.INFO
LOG_TO_EMAIL = False
EMAIL_LOG_LEVEL = logging.ERROR
EMAIL_LOG_SMTP_HOST = 'smtp.server.domain.fake'
EMAIL_LOG_FROM_ADDR = 'fishface@application.admin'
EMAIL_LOG_TO_ADDRS = ['fishface@application.admin']
EMAIL_LOG_SUBJECT = '[FISHFACE_LOG] Generic message'

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

LOG_FILE_PATH = os.path.join(VAR_LOG, 'fishface.log')

DJANGO_DIR = path_join(LIB, 'django')

REAL_POWER_SUPPLY = not is_file(ETC, 'FAKE_POWER_SUPPLY')

REAL_CAMERA = not is_file(ETC, 'FAKE_CAMERA')
CAMERA_RESOLUTION = (512, 384)
CAMERA_ROTATION = 180
CAMERA_CONSISTENCY_SETTINGS = [
    {
        'shutter_speed': 25596L,
        'awb_mode': 'off',
        'exposure_mode': 'off',
        'iso': 800,
        'saturation': -100,
        'contrast': 50,
        'brightness': 70,
    },
    {
        'awb_gains': (fractions.Fraction(187, 128), fractions.Fraction(375, 256)),
    }
]

NORMALIZED_SHAPE = (384, 512)
NORMALIZED_DTYPE = np.uint8

redis_hostname_file_path = path_join(VAR_RUN, 'redis.hostname')
REDIS_HOSTNAME = str(return_text_file_contents(redis_hostname_file_path))
REDIS_HOSTNAME = REDIS_HOSTNAME if REDIS_HOSTNAME else 'localhost'

redis_password_file_path = path_join(ETC, 'redis', 'redis_password')
REDIS_PASSWORD = str(return_text_file_contents(redis_password_file_path))

CELERY_BROKER_URL = 'redis://' + ((':' + REDIS_PASSWORD + '@') if REDIS_PASSWORD else '')
CELERY_BROKER_URL += REDIS_HOSTNAME

CELERY_RESULT_URL = CELERY_BROKER_URL

CELERY_QUEUE_NAMES = 'drone django learn cjc results psu camera johnny_cache cluster_dispatch eph'

CELERY_WORKER_CONCURRENCY = {
    'drone': 8,
    'results': 4,
}

ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1 = 2
ML_RESERVE_DATA_DENOMINATOR = 10
ML_STAGE_1_IMAGES_PER_CHUNK = 25

CJR_CREATION_TIMEOUT = 30
CAMERA_QUEUE_PRELOAD = 15

try:
    from local_settings.py import *
except ImportError:
    pass


def bash_exports():
    return 'export ' + ' '.join(['FF_{export_me}={value}'.format(
        export_me=export_me,
        value=globals()[export_me])
        for export_me in
        'ROOT ETC VAR VAR_RUN VAR_LOG LIB BIN VENV LOG_LEVEL'.split(' ')]
    )


def main():
    if sys.argv[1] == '--exports':
        print(bash_exports())

if __name__ == '__main__':
    main()