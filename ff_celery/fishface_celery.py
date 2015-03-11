import os
import celery

HOME = os.environ['HOME']
ALT_ROOT = HOME

celery_app = celery.Celery()
celery_app.config_from_object('ff_celery.celeryconfig')