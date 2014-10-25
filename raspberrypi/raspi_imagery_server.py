#!/usr/bin/env python

"""
This module is a small program intended to run on a Raspberry Pi with
attached camera module and send imagery to a FishFace server.
"""

import threading
import time
import io
import BaseHTTPServer
import urlparse
import requests
import datetime
import logging
import logging.handlers
import json
import cgi

import fishface_server_auth

logger = logging.getLogger('raspi')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

LOG_TO_CONSOLE = True
CONSOLE_LOG_LEVEL = logging.DEBUG
FILE_LOG_LEVEL = logging.DEBUG

console_handler = logging.StreamHandler()
console_handler.setLevel(CONSOLE_LOG_LEVEL)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('imagery_server.log')
file_handler.setLevel(FILE_LOG_LEVEL)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
if LOG_TO_CONSOLE:
    logger.addHandler(console_handler)

try:
    import picamera
    import instruments.hp as ik
    REAL_HARDWARE = True
    BASE_URL = "http://fishface/fishface/"
    logger.info("Running server on real Raspi hardware with an HP power supply.")
except ImportError:
    # noinspection PyPep8Naming
    import FakeHardware as picamera
    # noinspection PyPep8Naming
    import FakeHardware as ik
    REAL_HARDWARE = False
    BASE_URL = "http://localhost:8000/fishface/"
    logger.warning("Emulating raspi hardware.")
    logger.warning("Real data collection is disabled.")

HOST = ''
PORT = 18765

IMAGE_POST_URL = "{}upload_imagery/".format(BASE_URL)
TELEMETRY_URL = "{}telemetry/".format(BASE_URL)
CJR_URL = "{}cjr/".format(BASE_URL)
CJR_NEW_URL = "{}cjr/new_for_raspi/".format(BASE_URL)

DATE_FORMAT = "%Y-%m-%d-%H:%M:%S"


def delay_until(unix_timestamp):
    now = time.time()
    while now < unix_timestamp:
        time.sleep(unix_timestamp-now)
        now = time.time()


def delay_for_seconds(seconds):
    later = time.time() + seconds
    delay_until(later)


class CaptureJob(threading.Thread):
    def __init__(self, controller,
                 startup_delay, interval, duration,
                 voltage, current,
                 xp_id, species):
        super(CaptureJob, self).__init__(name='capturejob')
        self.logger = logging.getLogger('raspi.capturejob')
        self.logger.setLevel(logging.DEBUG)

        self.controller = controller

        self.status = 'staged'

        self.startup_delay = float(startup_delay)
        self.interval = float(interval)
        self.duration = float(duration)
        self.voltage = float(voltage)
        self.current = float(current)

        self.xp_id = xp_id
        self.species = species

        self.cjr_id = None

        self.total = None
        self.remaining = None

        self.capture_times = None
        self.job_ends_after = None

        self.start_timestamp = None
        self.stop_timestamp = None

        self._keep_looping = None

    def run(self):
        self.start_timestamp = time.time()

        self.logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup_delay'
        self.controller.set_psu({
            'enable_output': True,
            'voltage': self.voltage,
            'current': self.current,
        })

        payload = {
            'xp_id': self.xp_id,
            'voltage': self.voltage,
            'current': self.current,
            'start_timestamp': self.start_timestamp
        }

        self._keep_looping = True

        if self.interval > 0:
            logger.debug('cjr creation payload: {}'.format(payload))
            response = requests.post(CJR_NEW_URL, auth=(fishface_server_auth.USERNAME, fishface_server_auth.PASSWORD), data=payload)
            self.cjr_id = response.json()['cjr_id']
            self.job_with_capture()
        else:
            self.job_without_capture()

        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

        deathcry = self.get_status_dict()
        deathcry['command'] = 'job_status_update'

        self.controller.deathcry = deathcry

    def job_without_capture(self):
        self.total = 0
        self.remaining = 0

        self.logger.info('starting captureless wait period')
        self.controller.set_psu({
            'enable_output': True,
            'voltage': self.voltage,
            'current': self.current,
        })
        self.status = 'running'

        self.job_ends_after = time.time() + self.duration

        while self._keep_looping and time.time() < self.job_ends_after:
            delay_for_seconds(1)

    def job_with_capture(self):
        self.logger.info('preparing to capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))
        first_capture_at = self.start_timestamp + self.startup_delay

        self.logger.debug('first capture in {} seconds'.format(first_capture_at - time.time()))
        self.capture_times = [first_capture_at]
        for j in range(1, int(self.duration / self.interval)):
            self.capture_times.append(first_capture_at + j*self.interval)

        self.job_ends_after = self.capture_times[-1]
        self.total = len(self.capture_times)
        self.remaining = len(self.capture_times)

        for i, next_capture_time in enumerate(self.capture_times):
            delay_until(next_capture_time)
            self.status = 'running'
            if not self._keep_looping:
                break

            self.logger.debug('POSTing image to server')
            self.controller.server.post_current_image_to_server({
                'command': 'post_image',
                'xp_id': self.xp_id,
                'is_cal_image': 0,
                'cjr_id': self.cjr_id,
                'voltage': self.voltage,
                'current': self.current,
                'species': self.species,
            }, sync=False)
            self.logger.debug('POSTed image to server')

            self.remaining = self.total - i - 1

    def abort_job(self):
        self.logger.info('Job aborted: {}'.format(self.get_status_dict()))
        self.status = 'aborted'
        self._keep_looping = False

    def get_status_dict(self):
        return {
            'status': self.status,
            'xp_id': self.xp_id,
            'cjr_id': self.cjr_id,
            'species': self.species,
            'total': self.total,
            'voltage': self.voltage,
            'current': self.current,
            'remaining': self.remaining,
            'start_timestamp': self.start_timestamp,
            'stop_timestamp': self.stop_timestamp,
            'seconds_left': int(self.job_ends_in),
        }

    @property
    def job_ends_in(self):
        if self.job_ends_after is not None:
            ends_in = self.job_ends_after - time.time()
            return ends_in
        else:
            return 1000000

class CaptureJobController(threading.Thread):
    def __init__(self, imagery_server):
        super(CaptureJobController, self).__init__(name='capturejob_controller')
        self.logger = logging.getLogger('raspi.capturejob_controller')
        self.logger.setLevel(logging.DEBUG)

        self._queue = list()
        self._current_job = None
        self._staged_job = None

        self._deathcries = list()

        self._keep_controller_running = True

        self.server = imagery_server

    def run(self):
        if REAL_HARDWARE:
            wait_time = 3
        else:
            wait_time = 1
        self.logger.debug('Waiting {} seconds for the rest of the threads to catch up.'.format(wait_time))
        delay_for_seconds(wait_time)
        self.logger.info('CaptureJob Controller starting up.')
        while self._keep_controller_running:
            while len(self._deathcries):
                self.logger.info("Posting deathcries.  " +
                                 "Cries remaining to post: {}".format(len(self._deathcries)))
                self.server.telemeter.post_to_fishface(self.deathcry)

            if self._current_job is not None:
                self.logger.debug('Reporting on current job.')
                current_status = self.get_current_job_status()
                if current_status['cjr_id'] is not None:
                    current_status['command'] = 'job_status_update'
                    self.server.telemeter.post_to_fishface(current_status)

            if (self._staged_job is None and self._current_job is not None and not self._queue and
                (self._current_job.job_ends_after < time.time() or self._current_job.status == 'aborted')):
                self.logger.info('Current job is dead and there are no more pending.')
                self._current_job = None

            if self._current_job is None and self._staged_job is None and self._queue:
                self.logger.info('No jobs active, but jobs in queue.')
                self._current_job = CaptureJob(self, **self._queue.pop(0))
                self._current_job.start()
                self.logger.debug('Started new current job.')

            if ((self._current_job is None or self._current_job.job_ends_after < time.time()) and
                            self._staged_job is not None):
                self.logger.info('Current job is dead, promoting staged job.')
                self._current_job = self._staged_job
                self._current_job.start()
                self._staged_job = None

            if self._staged_job is None and self._queue and self._current_job.job_ends_in < 10:
                self.logger.info("New staged job being promoted from queue.")
                self._staged_job = CaptureJob(self, **self._queue.pop(0))

            if self._current_job is None and self._staged_job is None and not self._queue:
                if self.server.power_supply.voltage_sense > 0.1:
                    self.logger.info('Shutting down power supply until the next job arrives.')
                    self.set_psu({
                        'voltage': 0,
                        'current': 0,
                        'enable_output': 0,
                    })

            time.sleep(1)

    def get_current_job_status(self):
        return self._current_job.get_status_dict()

    def get_staged_job_status(self):
        return self._staged_job.get_status_dict()

    def abort_running_job(self):
        self.logger.info("Aborting current job.")
        self._current_job.abort_job()

    def abort_all(self, payload):
        self.logger.info("Aborting all jobs!")
        self._queue = list()
        self._staged_job = None
        self._current_job.abort_job()
        return payload

    def insert_job(self, job_spec, position):
        self.logger.info('Inserting job at position {} in queue.'.format(position))
        self._queue.insert(position, job_spec)

    def append_job(self, job_spec):
        self.logger.info('Appending job to queue.')
        self.insert_job(len(self._queue), job_spec)

    def set_psu(self, *args, **kwargs):
        self.logger.debug('Passing set_psu request up to the ImageryServer.')
        self.server.set_psu(*args, **kwargs)

    def complete_status(self, payload):
        response = {'command': 'job_status'}

        if self._current_job is not None:
            response['current_job'] = self.get_current_job_status()
            response['xp_id'] = response['current_job']['xp_id']
        else:
            response['xp_id'] = False

        if self._staged_job is not None:
            response['staged_job'] = self.get_staged_job_status()

        if self._queue:
            response['queue'] = self._queue
        else:
            response['queue'] = list()

        return response

    def set_queue(self, payload):
        queue = json.loads(payload['queue'])
        for job in queue:
            job['xp_id'] = int(payload['xp_id'])
            job['species'] = payload['species']
        self._queue = queue
        return payload

    def stop_controller(self):
        self.logger.info('Stopping capturejob controller.')
        self._keep_controller_running = False

    @property
    def deathcry(self):
        if self._deathcries:
            return self._deathcries.pop(0)
        return False

    @deathcry.setter
    def deathcry(self, deathcry):
        self._deathcries.append(deathcry)

class Telemeter(object):
    def __init__(self, imagery_server):
        self.logger = logging.getLogger('raspi.telemeter')
        self.logger.setLevel(logging.DEBUG)

        self.server = imagery_server

        logger.info("Telemeter instantiated.")

    def post_to_fishface(self, payload, files=None):
        logger.debug('POSTing payload to remote host:\n{}'.format(payload))

        payload = {'payload': json.dumps(payload)}

        if files is None:
            response = requests.post(TELEMETRY_URL, auth=(fishface_server_auth.USERNAME, fishface_server_auth.PASSWORD), data=payload)
        else:
            response = requests.post(TELEMETRY_URL, auth=(fishface_server_auth.USERNAME, fishface_server_auth.PASSWORD), data=payload, files=files)

        self.logger.info('POST response code: {}'.format(response.status_code))

        if response.status_code in [500, 410, 501]:
            logger.warning("Got {} status from server.".format(response.status_code))
            with open('/tmp/latest_raspi_{}.html'.format(response.status_code), 'w') as f:
                f.write(response.text)
        else:
            return response.json()

    def handle_received_post(self, request):
        logger.debug('telemeter received POST payload from remote host:\n{}'.format(request))

        method = self.server.command_dispatch.get(request['command'], self.unrecognized_command)
        result = method(request)
        logger.debug("result of method was: {}".format(result))

        return result

    def unrecognized_command(self, payload):
        logger.info("Unrecognized command received from server:\n{}".format(payload))


class ImageryServer(object):
    """
    """

    def __init__(self):
        self.capturejob_controller = CaptureJobController(self)
        self.capturejob_controller.start()

        self._keep_capturing = True
        self._keep_capturejob_looping = True

        if REAL_HARDWARE:
            # self.power_supply = ik.HP6652a.open_serial('/dev/ttyUSB0', 57600)
            self.power_supply = ik.HP6652a.open_gpibusb('/dev/ttyUSB0', 1)
        else:
            self.power_supply = ik.HP6652a()

        self.camera = picamera.PiCamera()
        self.camera.resolution = (2048, 1536)
        self.camera.rotation = 180

        self._job_status = None

        self._current_frame = None
        self._current_frame_capture_time = None

        self.telemeter = Telemeter(self)

        self.command_dispatch = {
            'set_psu': self.set_psu,
            'post_image': self.post_current_image_to_server,

            'insert_job': self.capturejob_controller.insert_job,
            'job_status': self.capturejob_controller.complete_status,

            'set_queue': self.capturejob_controller.set_queue,

            'abort_running_job': self.capturejob_controller.abort_running_job,
            'abort_all': self.capturejob_controller.abort_all,
        }

    def _capture_new_current_frame(self):
        stream = io.BytesIO()
        new_frame_capture_time = time.time()
        self.camera.capture(
            stream,
            format='jpeg'
        )

        image = stream.getvalue()

        self._current_frame = image
        self._current_frame_capture_time = new_frame_capture_time

    def post_current_image_to_server(self, payload, sync=True):
        current_frame = self._current_frame
        current_frame_capture_time = self._current_frame_capture_time

        stream = io.BytesIO(current_frame).read()

        image_dtg = datetime.datetime.fromtimestamp(
            float(current_frame_capture_time)
        ).strftime(
            DATE_FORMAT
        )

        since_epoch = time.time()

        image_filename = 'XP-{}_CJR-{}_{}_{}_{}.jpg'.format(
            payload['xp_id'],
            payload['cjr_id'],
            payload['species'],
            image_dtg,
            since_epoch,
        )

        logger.debug('posting image {}'.format(image_filename))

        is_cal_image = (str(payload['is_cal_image']).lower()
                        in ['true', 't', 'yes', 'y', '1'])

        payload['filename'] = image_filename
        payload['capture_time'] = current_frame_capture_time
        payload['is_cal_image'] = str(is_cal_image)

        files = {image_filename: stream}

        image_start_post_time = time.time()

        if sync:
            self.telemeter.post_to_fishface(payload, files=files)
            logger.debug("image posted in {} seconds".format(time.time() - image_start_post_time))
        else:
            def async_image_post(url, files_unshadow, payload_unshadow):
                async_logger = logging.getLogger('raspi.async_image_post')
                self.telemeter.post_to_fishface(payload_unshadow, files=files_unshadow)
                async_logger.debug("image posted async in {} seconds".format(time.time() - image_start_post_time))

            async_thread = threading.Thread(
                target=async_image_post,
                args=(TELEMETRY_URL, files, payload)
            )
            async_thread.start()

        return payload

    def get_current_frame(self):
        return self._current_frame

    def run(self):
        def image_capture_loop():
            while self._keep_capturing:
                self._capture_new_current_frame()
            self.camera.close()

        thread = threading.Thread(name='capture', target=image_capture_loop)
        logger.info("starting capture thread loop")
        thread.start()

        logger.info("capture thread loop started")

        server_address = (HOST, PORT)
        httpd = BaseHTTPServer.HTTPServer(
            server_address,
            CommandHandler
        )
        httpd.parent = self

        logger.info("starting http server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self._keep_capturing = False
            self._keep_capturejob_looping = False
            self.capturejob_controller.stop_controller()
            httpd.server_close()

    def set_psu(self, payload):
        if bool(int(payload.get('reset', False))):
            self.power_supply.reset()
            return False

        voltage = float(payload.get('voltage', False))
        current = float(payload.get('current', False))
        enable_output = bool(int(payload.get('enable_output', False)))

        if voltage:
            logger.debug("setting psu voltage to {} V".format(
                voltage
            ))
            self.power_supply.voltage = voltage

        if current:
            logger.debug("setting psu max current to {} A".format(
                current
            ))
            self.power_supply.current = current

        if enable_output:
            logger.debug("enabling psu output")
        else:
            logger.debug("disabling psu output")

        self.power_supply.output = enable_output

        thread = threading.Thread(
            name='psu_sensed_data',
            target=self.post_power_supply_sensed_data,
            args=(payload, 1,)
        )
        thread.start()

        return False

    def post_power_supply_sensed_data(self, payload, delay=None):
        if delay is not None:
            time.sleep(delay)
        payload['command'] = 'power_supply_log'
        payload['voltage_meas'] = float(
            self.power_supply.voltage_sense)
        payload['current_meas'] = float(
            self.power_supply.current_sense)

        logger.debug('Posting psu sensed data:\n{}'.format(payload))

        self.telemeter.post_to_fishface(payload)


class CommandHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # noinspection PyPep8Naming
    def do_GET(self):
        logger.debug("Legacy GET request received.")
        self.send_response(410)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write('<html><body>GET REQUESTS NO LONGER SUPPORTED</body></html>')

    # noinspection PyPep8Naming
    def do_OPTIONS(self):
        origin = self.headers.getheader('Origin')

        logger.debug("OPTIONS request received.")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Method", "POST")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()


    # noinspection PyPep8Naming
    def do_POST(self):
        logger.debug("POST request received.")

        ctype, pdict = cgi.parse_header(self.headers.getheader('Content-Type'))
        if ctype == 'application/json':
            length = int(self.headers.getheader('content-length'))
            json_vars = json.loads(self.rfile.read(length))
        else:
            raise Exception("Can only accept 'application/json' POST requests.")

        logger.debug('json_vars:\n{}'.format(json_vars.keys()))

        result = self.server.parent.telemeter.handle_received_post(json_vars)

        logger.debug("Telemeter returned: '{}'".format(result))

        if result and result.get('command', False):
            payload = json.dumps(result)
            logger.debug("Sending response: {}".format(payload))
            self.send_response(200)
            self.send_header("content-type", "application/json")
            # self.send_header("content-length", len(payload))
            self.end_headers()
            self.wfile.write(payload)


def main():
    logger.info("Starting Raspi unprivileged server.")

    imagery_server = ImageryServer()

    imagery_server.run()

    logger.info("Exiting Raspi unprivileged server.")


if __name__ == '__main__':
    main()
