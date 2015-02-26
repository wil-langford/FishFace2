import os
import logging

from kombu import Queue, Exchange

# Groundwork

_HOME = os.environ['HOME']
_ALT_ROOT = _HOME

_password_filename = os.path.join(_ALT_ROOT, 'etc', 'redis', 'redis_password')

try:
    with open(_password_filename, 'rt') as f:
        _redis_password = f.read().strip()
except IOError:
    logging.warning('No redis password found.  Disabling redis authentication.')
    _redis_password = False

try:
    with open(os.path.join(_ALT_ROOT, 'var', 'run', 'redis.hostname'), 'rt') as f:
        _redis_hostname = f.read().strip()
except IOError:
    _redis_hostname = 'localhost'

if _redis_password:
    _broker_url = 'redis://:{password}@{hostname}'.format(
        password=_redis_password, hostname=_redis_hostname)
    _result_url = _broker_url
else:
    _broker_url = 'redis://{hostname}'.format(hostname=_redis_hostname)
    _result_url = _broker_url


class FishfaceRouter(object):
    @staticmethod
    def route_for_task(self, task, args=None, kwargs=None):
        task_category = task.split('.')[0]
        if task_category in ['tasks', 'results']:
            route = {
                'exchange': 'FishFace',
                'exchange_type': 'direct',
                'routing_key': 'fishface.{}'.format(task_category),
            }
        else:
            route = {
                'exchange': 'default',
                'exchange_type': 'direct',
                'routing_key': 'default',
            }

        return route


# Actual Celery configuration

BROKER_URL = _broker_url
CELERY_RESULT_BACKEND = _result_url

CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'

CELERY_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('tasks', Exchange('FishFace'), routing_key='fishface.tasks'),
    Queue('results', Exchange('FishFace'), routing_key='fishface.results'),
)

CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_ROUTES = (FishfaceRouter(), )