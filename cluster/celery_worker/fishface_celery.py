import os
import celery

ALT_ROOT = os.environ['HOME']

with open(os.path.join(ALT_ROOT, 'etc', 'redis', 'redis_password'), 'rt') as f:
    password = f.read().strip()

with open(os.path.join(ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
    hostname = f.read().strip()

broker_url = 'redis://{}'.format(hostname)
result_url = broker_url

# # Authentication is broken at the moment.
# broker_url = 'redis://:{}@{}'.format(password, hostname)
# result_url = u'redis://{}'.format(hostname)

app = celery.Celery('tasks')
app.conf.BROKER_URL = broker_url
app.conf.CELERY_RESULT_BACKEND = result_url
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
app.conf.CELERY_TASK_SERIALIZER = 'pickle'
app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
