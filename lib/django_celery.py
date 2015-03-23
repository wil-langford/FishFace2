from __future__ import absolute_import

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lib.django.django_fishface.settings')
from django.conf import settings

celery_app = Celery()
celery_app.config_from_object('etc.celeryconfig')

celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)