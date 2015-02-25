from __future__ import absolute_import, print_function

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
from django.conf import settings

HOME = os.environ['HOME']
ALT_ROOT = HOME

app = Celery()

app.config_from_object('celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))