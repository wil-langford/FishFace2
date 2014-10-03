import logging
import json

import requests

from django.conf import settings

logger = logging.getLogger('djff.telemeter')


class Telemeter(object):
    def __init__(self):
        pass

    def post_to_raspi(self, payload, files=None):
        logger.debug('POSTing JSON payload to remote host:\n{}'.format(payload))

        json_payload = json.dumps(payload)

        headers = {'content-type': 'application/json'}

        if files is None:
            response = requests.post(
                settings.TELEMETRY_URL,
                data=json_payload,
                headers=headers,
            )
        else:
            raise NotImplemented("Can't POST files to the Raspi.")

        if response.status_code in [500, 410]:
            with open('/tmp/latest_djff_{}.html'.format(response.status_code), 'w') as f:
                f.write(response.text)

        response_json = response.json()

        return response_json
