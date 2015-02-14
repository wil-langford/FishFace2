import os
import celery

with open(os.path.join(os.environ['HOME'], 'var', 'run', 'redis.hostname'), 'rt') as f:
    hostname = f.read().strip()

redis_url = 'redis://{}'.format(hostname)

app = celery.Celery('tasks', backend=redis_url, broker=redis_url)
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
app.conf.CELERY_TASK_SERIALIZER = 'pickle'
app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
