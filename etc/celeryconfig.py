import os

from kombu import Queue, Exchange

from lib.fishface_logging import logger

import etc.fishface_config as ff_conf

# Groundwork


# Task router based on task name
class FishFaceRouter(object):
    @staticmethod
    def route_for_task(task, args=None, kwargs=None):
        route = None
        task_category = task.split('.')[0]

        if task_category in ff_conf.CELERY_QUEUE_NAMES:
            route = {
                'exchange': 'fishface',
                'exchange_type': 'direct',
                'routing_key': 'fishface.{}'.format(task_category),
            }

        if route is None:
            route = {
                'exchange': 'default',
                'exchange_type': 'direct',
                'routing_key': 'default',
            }

        return route


# Actual Celery configuration
BROKER_URL = ff_conf.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = ff_conf.CELERY_RESULT_URL

CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'

fishface_exchange = Exchange('fishface')

CELERY_QUEUES = tuple(
    [Queue('default', Exchange('default'), routing_key='default')] +
    [Queue(name, fishface_exchange, routing_key='fishface.' + name)
     for name in ff_conf.CELERY_QUEUE_NAMES]
)

CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_ROUTES = (FishFaceRouter(), )