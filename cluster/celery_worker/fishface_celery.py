import os
import celery



HOME = os.environ['HOME']
ALT_ROOT = HOME

app = celery.Celery()
app.config_from_object('celeryconfig')