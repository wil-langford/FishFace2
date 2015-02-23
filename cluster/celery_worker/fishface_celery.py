import os
import celery

ALT_ROOT = os.environ['HOME']

with open(os.path.join(ALT_ROOT, 'etc', 'redis', 'redis_password'), 'rt') as f:
    password = f.read().strip()

with open(os.path.join(ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
    hostname = f.read().strip()

broker_url = 'redis://:{}@{}'.format(password, hostname)
result_url = 'redis://{}'.format(hostname)

app = celery.Celery('tasks', backend=result_url, broker=broker_url)
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
app.conf.CELERY_TASK_SERIALIZER = 'pickle'
app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
