import os
import celery

ALT_ROOT = os.environ['HOME']

with open(os.path.join(ALT_ROOT, 'etc', 'redis', 'redis_password'), 'rt') as f:
    password = f.read().strip()

with open(os.path.join(ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
    hostname = f.read().strip()

redis_url = 'redis://:{}@{}'.format(password, hostname)

app = celery.Celery('tasks', backend=redis_url, broker=redis_url)
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
app.conf.CELERY_TASK_SERIALIZER = 'pickle'
app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
