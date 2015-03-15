import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
from django.conf import settings

celery_app = Celery()
celery_app.config_from_object('ff_celery.celeryconfig')

celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)