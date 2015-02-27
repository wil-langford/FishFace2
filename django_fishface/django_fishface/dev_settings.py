import os

DEBUG = False
TEMPLATE_DEBUG = False

DEV_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DEV_BASE_DIR, 'db.sqlite3'),
    }
}

IMAGERY_SERVER_HOST = 'localhost'
IMAGERY_SERVER_PORT = 18765