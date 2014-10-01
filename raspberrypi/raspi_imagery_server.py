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
    BASE_URL = "http://fishfacehost:8000/fishface/"
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
    def __init__(self, controller, startup_delay, interval, duration, voltage, current, xp_id):
        super(CaptureJob, self).__init__(name='capturejob')
        self.logger = logging.getLogger('raspi.capturejob')

        self.controller = controller

        self.status = 'staged'

        self.startup_delay = startup_delay
        self.interval = interval
        self.duration = duration
        self.voltage = voltage
        self.current = current

        self.xp_id = xp_id

        self.cjr_id = None

        self.total = None
        self.remaining = None

        self.capture_times = None

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

        delay_for_seconds(self.startup_delay)

        self.status = 'running'

        payload = {
            'xp_id': self.xp_id,
            'voltage': self.voltage,
            'current': self.current,
            'start_timestamp': self.start_timestamp
        }

        response = requests.post(CJR_NEW_URL, data=payload)
        self.cjr_id = response.json()['cjr_id']

        if self.interval > 0:
            self.job_with_capture()
        else:
            self.job_without_capture()

        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

    def job_without_capture(self):
        self.logger.info('starting captureless wait period')
        self.controller.set_psu({
            'enable_output': True,
            'voltage': self.voltage,
            'current': self.current,
        })

        stop_at = time.time() + self.duration

        while self._keep_looping and time.time() < stop_at:
            time.sleep(1)

    def job_with_capture(self):
        self.logger.info('preparing to capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))
        first_capture_at = self.start_timestamp + self.startup_delay

        self.capture_times = [first_capture_at]
        for j in range(1, int(self.duration / self.interval) + 1):
            self.capture_times.append(first_capture_at + j*self.interval)

        self.total = len(self.capture_times) + 1
        self.remaining = len(self.capture_times) - 1

        for i, next_capture_time in enumerate(self.capture_times):
            delay_until(next_capture_time)
            if not self._keep_looping:
                break

            self.controller.post_current_image_to_server(self, sync=False)

            self.remaining = self.total - i

    def abort_job(self):
        self.status = 'aborted'
        self._keep_looping = False

    def get_status_dict(self):
        # status xp_id cjr_id total remaining start_timestamp stop_timestamp
        return {
            'status': self.status,
            'xp_id': self.xp_id,
            'cjr_id': self.cjr_id,
            'total': self.total,
            'remaining': self.remaining,
            'start_timestamp': self.start_timestamp,
            'stop_timestamp': self.stop_timestamp,
        }


class CaptureJobController(threading.Thread):
    def __init__(self, imagery_server):
        super(CaptureJobController, self).__init__(name='capturejob_controller')
        self.logger = logging.getLogger('raspi.capturejob_controller')

        self._queue = list()
        self._current_job = None
        self._staged_job = None

        self._keep_controller_running = True

        self.server = imagery_server

    def run(self):
        wait_time = 3
        self.logger.debug('Waiting {} seconds for the rest of the threads to catch up.'.format(wait_time))
        delay_for_seconds(wait_time)
        self.logger.info('CaptureJob Controller starting up.')
        while self._keep_controller_running:
            if self._current_job is not None:
                self.logger.debug('Reporting on current job.')
                self.get_current_job_status()

            if self._current_job is None and self._staged_job is None and self._queue:
                self.logger.info('No jobs active, but jobs in queue.')
                self._current_job = CaptureJob(**self._queue.pop(0))
                self._current_job.start()
                self.logger.debug('Started new current job.')

                if self._queue:
                    self._staged_job = CaptureJob(**self._queue.pop(0))
                    self.logger.debug('Staged new job.')

            if (self._current_job is None or not self._current_job.is_alive()) and self._staged_job is not None:
                self.logger.info('Current job is dead, promoting staged job.')
                self._current_job = self._staged_job
                self._current_job.start()
                self._staged_job = None

            if self._staged_job is None and self._queue and self._current_job.remaining < 5:
                self.logger.info("New staged job being promoted from queue.")
                self._staged_job = CaptureJob(**self._queue.pop(0))

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

    def abort_running_job(self):
        self.logger.info("Aborting current job.")
        self._current_job.abort_job()

    def abort_all(self):
        self.logger.info("Aborting all jobs!")
        self._staged_job = None
        self._queue = list()
        self._current_job.abort_job()

    def insert_job(self, job_spec, position):
        self.logger.info('Inserting job at position {} in queue.'.format(position))
        self._queue.insert(position, job_spec)

    def append_job(self, job_spec):
        self.logger.info('Appending job to queue.')
        self.insert_job(len(self._queue), job_spec)

    def set_psu(self, *args, **kwargs):
        self.logger.debug('Passing set_psu request up to the ImageryServer.')
        self.server.set_psu(*args, **kwargs)

    def complete_status(self):
        return {
            'current': self._current_job.get_status_dict(),
            'staged': self._staged_job.get_status_dict(),
            'queue': self._queue,
        }

    def stop_controller(self):
        self.logger.info('Stopping capturejob controller.')
        self._keep_controller_running = False


class Telemeter(object):
    def __init__(self, imagery_server):
        self.logger = logging.getLogger('raspi.Telemeter')
        self.server = imagery_server

    def post_to_fishface(self, payload, files=None):
        self.logger.debug('POSTing payload to remote host:\n{}'.format(payload))

        if not isinstance(payload, basestring):
            payload = json.dumps(payload)

        if files is None:
            response = requests.post(TELEMETRY_URL, data=payload)
        else:
            response = requests.post(TELEMETRY_URL, data=payload, files=files)

        if response.status_code in [500, 410, 501]:
            with open('/tmp/latest_djff_{}.html'.format(response.status_code), 'w') as f:
                f.write(response.text)
        else:
            return response.json()

    def handle_received_post(self, post_vars):
        payload = post_vars.get('payload', False)

        if not payload:
            return False

        self.logger.debug('received POST payload from remote host:\n{}'.format(payload))

        method = self.server.command_dispatch.get(payload['command'], self.unrecognized_command)
        result = method(payload)

        if not result.get('no_reply', False):
            return json.dumps(result)
        else:
            return ''

    def unrecognized_command(self, payload):
        self.logger.info("Unrecognized command received from server:\n{}".format(payload))


class ImageryServer(object):
    """
    """

    def __init__(self):
        self.capturejob_controller = CaptureJobController(self)
        self.capturejob_controller.start()

        self._keep_capturing = True
        self._keep_capturejob_looping = True

        if REAL_HARDWARE:
            self.power_supply = ik.HP6652a.open_serial('/dev/ttyUSB0', 57600)
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
                async_logger.debug("image posted in {} seconds".format(time.time() - image_start_post_time))

            async_thread = threading.Thread(
                target=async_image_post,
                args=(IMAGE_POST_URL, files, payload)
            )
            async_thread.start()

        return False

    def get_current_frame(self):
        return self._current_frame

    def run(self):
        def image_capture_loop():
            while self._keep_capturing:
                self._capture_new_current_frame()
            self.camera.close()

        thread = threading.Thread(name='capture' ,target=image_capture_loop)
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
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    # noinspection PyPep8Naming
    def do_GET(self):
        self.send_response(410)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(str('GET REQUESTS NO LONGER SUPPORTED'))

    # noinspection PyPep8Naming
    def do_POST(self):
        ctype, pdict = urlparse.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            post_vars = urlparse.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            post_vars = urlparse.parse_qs(
                self.rfile.read(length),
                keep_blank_values=1)
        else:
            post_vars = {}

        result = self.server.parent.telemeter.handle_received_post(post_vars)

        if result:
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()
            self.wfile.write(str(result))


def main():
    logger.info("Starting Raspi unprivileged server.")

    imagery_server = ImageryServer()

    imagery_server.run()

    logger.info("Exiting Raspi unprivileged server.")


if __name__ == '__main__':
    main()