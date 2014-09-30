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
import json

logger = logging.getLogger('djff.raspi')

try:
    REAL_HARDWARE = True
    BASE_URL = "http://fishfacehost:8000/fishface/"
    import picamera
    import instruments.hp as ik
    logger.info("Running server on real Raspi hardware.")
except ImportError:
    REAL_HARDWARE = False
    BASE_URL = "http://localhost:8000/fishface/"
    # noinspection PyPep8Naming
    import FakeHardware as picamera
    import FakeHardware as ik
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
        super(CaptureJob, self).__init__()

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

        logger.info("starting up job for experiment {}".format(self.xp_id))
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
        logger.info('starting captureless wait period')
        self.controller.set_psu({
            'enable_output': True,
            'voltage': self.voltage,
            'current': self.current,
        })

        stop_at = time.time() + self.duration

        while self._keep_looping and time.time() < stop_at:
            time.sleep(1)

    def job_with_capture(self):
        logger.info('preparing to capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))
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
        super(CaptureJobController, self).__init__()
        self._queue = list()
        self._current_job = dict()
        self._staged_job = dict()

        self._keep_controller_running = True

        self.server = imagery_server

    def run(self):
        while self._keep_controller_running:
            if self._current_job is not None and self._current_job.is_alive():
                self.report_current_job_status()
                if self._staged_job:
                    self._current_job = self._staged_job
                    self._current_job.start()

                    if self._queue:
                        self._staged_job = CaptureJob(**self._queue.pop(0))

            time.sleep(1)

    def report_current_job_status(self):
        return self._current_job.get_status_dict()

    def abort_running_job(self):
        self._current_job.abort_job()

    def abort_all(self):
        self._staged_job = None
        self._queue = list()
        self._current_job.abort_job()

    def insert_job(self, job_spec, position):
        self._queue.insert(position, job_spec)

    def set_psu(self, *args, **kwargs):
        self.server.set_psu(*args, **kwargs)

    def complete_status(self):
        return {
            'current': self._current_job.get_status_dict(),
            'staged': self._staged_job.get_status_dict(),
            'queue': self._queue,
        }


class Telemeter(object):
    def __init__(self, imagery_server):
        self.server = imagery_server

    def post_to_fishface(self, payload, files=None):
        logger.debug('POSTing payload to remote host:\n{}'.format(payload))

        if not isinstance(payload, basestring):
            payload = json.dumps(payload)

        if files is None:
            response = requests.post(TELEMETRY_URL, data=payload)
        else:
            response = requests.post(TELEMETRY_URL, data=payload, files=files)

        if response.status_code in [500, 501]:
            with open('/tmp/latest_djff_{}.html'.format(response.status_code), 'w') as f:
                f.write(response.text)

    def handle_received_post(self, post_vars):
        payload = post_vars.get('payload', False)

        if not payload:
            return False

        logger.debug('received POST payload from remote host:\n{}'.format(payload))

        method = self.server.command_dispatch.get(payload['command'], self.unrecognized_command)
        result = method(payload)

        if not result.get('no_reply', False):
            return json.dumps(result)

    def unrecognized_command(self, payload):
        pass


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

        t = time.time()

        if sync:
            r = requests.post(
                IMAGE_POST_URL,
                files=files,
                data=payload
            )
            logger.debug("image posted in {} seconds".format(
                time.time() - t
            ))
            if r.status_code == 500:
                with open('/tmp/latest_500.html', 'w') as f:
                    f.write(r.text)

            return r
        else:
            def async_image_post(url, files_to_post, metadata_to_post):
                result = requests.post(
                    url,
                    files=files_to_post,
                    data=metadata_to_post
                )
                if result.status_code == 500:
                    with open('/tmp/latest_500.html', 'w') as latest_500_file:
                        latest_500_file.write(result.text)
                return result

            async_thread = threading.Thread(
                target=async_image_post,
                args=(IMAGE_POST_URL, files, payload)
            )
            async_thread.start()
            return

    def get_current_frame(self):
        return self._current_frame

    def run(self):
        def image_capture_loop():
            while self._keep_capturing:
                self._capture_new_current_frame()
            self.camera.close()

        thread = threading.Thread(target=image_capture_loop)
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
            self.wfile.write(str(result))


def main():
    print "Starting Raspi unprivileged server."

    imagery_server = ImageryServer()

    imagery_server.run()

    print "\nExiting Raspi unprivileged server."


if __name__ == '__main__':
    main()