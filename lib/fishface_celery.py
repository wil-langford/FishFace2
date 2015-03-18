import os
import celery

celery_app = celery.Celery()
celery_app.config_from_object('etc.celeryconfig')