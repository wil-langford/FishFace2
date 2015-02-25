import os
import celery

HOME = os.environ['HOME']
ALT_ROOT = HOME
CLUSTER_DIR = os.path.join(ALT_ROOT, 'FishFace2', 'cluster')

# TODO: replace this antipattern
import site
site.addsitedir(CLUSTER_DIR)

PASSWORD_FILENAME = os.path.join(ALT_ROOT, 'etc', 'redis', 'redis_password')

AUTHENTICATE = os.path.isfile(PASSWORD_FILENAME)

if AUTHENTICATE:
    with open(PASSWORD_FILENAME, 'rt') as f:
        redis_password = f.read().strip()

with open(os.path.join(ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
    redis_hostname = f.read().strip()

if AUTHENTICATE:
    broker_url = 'redis://:{password}@{hostname}'.format(
        password=redis_password, hostname=redis_hostname)
    result_url = broker_url
else:
    broker_url = 'redis://{hostname}'.format(password=redis_password)
    result_url = broker_url

app = celery.Celery('tasks', broker=broker_url, backend=result_url)
app.conf.CELERY_ACCEPT_CONTENT = ['pickle', 'json']
app.conf.CELERY_TASK_SERIALIZER = 'pickle'
app.conf.CELERY_RESULT_SERIALIZER = 'pickle'
