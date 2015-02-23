import os
import celery

ALT_ROOT = os.environ['HOME']

PASSWORD_FILENAME = os.path.join(ALT_ROOT, 'etc', 'redis', 'redis_password')

AUTHENTICATE = os.path.isfile(PASSWORD_FILENAME)

if AUTHENTICATE:
    with open(PASSWORD_FILENAME, 'rt') as f:
        redis_password = f.read().strip()

with open(os.path.join(ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
    redis_hostname = f.read().strip()

app = celery.Celery('tasks')

app.config_from_object('celeryconfig')

app.conf.BROKER_TRANSPORT = app.conf.CELERY_RESULT_BACKEND = 'redis'
app.conf.BROKER_HOST = app.conf.CELERY_REDIS_HOST = redis_hostname
app.conf.CELERY_TASK_SERIALIZER = app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
if AUTHENTICATE:
    app.conf.BROKER_PASSWORD = app.conf.CELERY_REDIS_PASSWORD = redis_password
