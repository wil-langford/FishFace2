"""
Django settings for django_fishface project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.utils.crypto import get_random_string

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PASSWD_FILE = os.path.expanduser('~/fishface_db_password')

# These get imported/generated later.
DB_PASSWD = None
SECRET_KEY = None

def generate_and_collect_secret_keys():
    length = 50
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    django_key =  get_random_string(length, chars)

    with open(DB_PASSWD_FILE, 'r') as f:
        db_key = f.read().strip()

    with open(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'secret_keys.py'), 'w') as f:
        f.write(
            """SECRET_KEY = '{}'\nDB_PASSWD = '{}'""".format(
                django_key, db_key)
        )

try:
    from secret_keys import *
except ImportError:
    generate_and_collect_secret_keys()
    from secret_keys import *


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'djff',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'django_fishface.urls'

WSGI_APPLICATION = 'django_fishface.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'fishfacedb',
        'USER': 'fishfacedbuser',
        'PASSWORD': DB_PASSWD,
        'HOST': 'localhost',
        'PORT': '',
    },
    'dev': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = False

USE_TZ = True

DATETIME_FORMAT = 'Y-m-d H:i:s.u'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

# TODO: Change to a non-temporary MEDIA_ROOT after move to server.
MEDIA_ROOT = '/home/wil/PycharmProjects/FishFace2/eph/media/'
MEDIA_URL = '/media/'