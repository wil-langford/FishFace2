import logging
import json

import requests

from django.conf import settings

logger = logging.getLogger('djff.telemeter')


class Telemeter(object):
    def __init__(self, imagery_server):
        self.server = imagery_server

    def post_to_raspi(self, payload, files=None):
        logger.debug('POSTing payload to remote host:\n{}'.format(payload))

        if not isinstance(payload, basestring):
            payload = json.dumps(payload)

        if files is None:
            response = requests.post(settings.TELEMETRY_URL, data=payload)
        else:
            response = requests.post(settings.TELEMETRY_URL, data=payload, files=files)

        if response.status_code in [500, 410]:
            with open('/tmp/latest_djff_{}.html'.format(response.status_code), 'w') as f:
                f.write(response.text)

        return response.json()
