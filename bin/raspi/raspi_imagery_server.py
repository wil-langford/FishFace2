#!/usr/bin/env python

"""
This module is a small program intended to run on a Raspberry Pi with
attached camera module and send imagery to a FishFace server.
"""

import threading
import Queue
import time
import io
import BaseHTTPServer
import SocketServer
import datetime
import logging
import logging.handlers
import json
import cgi
import sys

import requests

import fishface_server_auth
from lib.fishface_logging import logger


try:
    import picamera
    import lib.RobustPowerSupply as RobustPowerSupply
    import lib.FakeHardware as FakeHardware
    from serial.serialutil import SerialException
    REAL_HARDWARE = True
    BASE_URL = "http://fishface/fishface/"
    logger.info("Running server on real Raspi hardware with an HP power supply.")
except ImportError:
    # noinspection PyPep8Naming
    import lib.FakeHardware as picamera
    # noinspection PyPep8Naming
    import lib.FakeHardware as ik

    class SerialException(IOError):
        pass

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
        time.sleep(unix_timestamp - now)
        now = time.time()


def delay_for_seconds(seconds):
    later = time.time() + seconds
    delay_until(later)


class RegisteredThreadWithHeartbeat(threading.Thread):
    """
    Remember to override the _heartbeat_run(), _run_at_start(), and _run_at_end() methods.
    """

    def __init__(self,
                 thread_registry, heartbeat_interval=1.0,
                 heartbeat_publish_interval=None,
                 *args, **kwargs):
        super(RegisteredThreadWithHeartbeat, self).__init__(*args, **kwargs)

        self._heartbeat_count = 0
        self._heartbeat_timestamp = None
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_publish_interval = heartbeat_publish_interval
        self._heartbeat_lock = threading.Lock()

        self._keep_looping = True
        self.ready = False

        self._thread_registry = thread_registry

        self._last_known_registry_index = len(self._thread_registry)
        thread_registry.append(self)

        logger.debug('{} thread initialized.'.format(self.name))

    def run(self):
        logger.debug('{} thread started.'.format(self.name))
        try:
            self._pre_run()

            while self._keep_looping:
                self._heartbeat_run()
                self.beat_heart()
                delay_for_seconds(self._heartbeat_interval)
        finally:
            self._post_run()

    def set_ready(self):
        logger.info('{} thread reports that it is ready.'.format(self.name))
        self.ready = True

    def _heartbeat_run(self):
        raise NotImplementedError

    def _pre_run(self):
        self.set_ready()

    def _post_run(self):
        pass

    def beat_heart(self):
        with self._heartbeat_lock:
            self._heartbeat_timestamp = time.time()
            self._heartbeat_count += 1

        if self._heartbeat_publish_interval is not None:
            if not self._heartbeat_count % self._heartbeat_publish_interval:
                logger.debug('{} thread heartbeat count is {}'.format(self.name,
                                                                      self._heartbeat_count))

    @property
    def heartbeat_count(self):
        return self._heartbeat_count

    def _set_name(self, new_name):
        new_name_str = str(new_name)
        logger.info("Renaming thread '{}' to '{}'.".format(self.name, new_name_str))
        self.name = new_name_str

    @property
    def last_heartbeat(self):
        return self._heartbeat_timestamp

    @property
    def last_heartbeat_delta(self):
        if self._heartbeat_timestamp is not None:
            return time.time() - self._heartbeat_timestamp
        else:
            return 1000000

    @property
    def index_in_registry(self):
        if self._thread_registry[self._last_known_registry_index] is self:
            return self._last_known_registry_index

        if self._thread_registry is None:
            return None

        for idx, thr in self._thread_registry:
            if thr is self:
                return idx

        raise Exception("Thread named {} is not in the registry.".format(self.name))

    def abort(self):
        self._keep_looping = False
        logger.info('Thread {} aborted.'.format(self.name))


class CaptureJob(RegisteredThreadWithHeartbeat):
    def __init__(self, controller,
                 startup_delay, interval, duration,
                 voltage, current,
                 xp_id, species,
                 thread_registry,
                 open_camera_method,
                 close_camera_method,
                 *args, **kwargs):
        super(CaptureJob, self).__init__(thread_registry,
                                         name='capturejob',
                                         *args, **kwargs)
        self.logger = logging.getLogger('raspi.capturejob')
        self.logger.setLevel(logging.DEBUG)

        self.open_camera = open_camera_method
        self.close_camera = close_camera_method

        self.controller = controller
        self.publish_deathcry = self.controller.publish_deathcry

        self.status = 'staged'

        self.startup_delay = float(startup_delay)
        self.interval = float(interval)
        self.duration = float(duration)
        self.voltage = float(voltage)
        self.current = float(current)

        self.xp_id = xp_id
        self.species = species

        if self.interval <= 0:
            self.name = 'job_without_capture_{}_seconds_at_{}_volts'.format(
                self.duration, self.voltage
            )
            self._captureless = True
            self._heartbeat_run = self._job_without_capture
            self._heartbeat_interval = 0
        else:
            self.name = 'XP_{}_CJR_pending_id'.format(self.xp_id)
            self._captureless = False
            self._heartbeat_run = self._job_with_capture
            self._heartbeat_interval = 1

        self.cjr_id = None

        self.total = None
        self.remaining = None

        self.capture_times = None
        self.job_ends_after = None

        self.start_timestamp = None
        self.stop_timestamp = None

        self._heartbeat_cj = 0

    def _pre_run(self):
        self.start_timestamp = time.time()

        self.logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup_delay'

        payload = {
            'xp_id': self.xp_id,
            'voltage': self.voltage,
            'current': self.current,
            'start_timestamp': self.start_timestamp
        }

        self.controller.set_psu({
            'enable_output': bool(self.voltage),
            'voltage': self.voltage,
            'current': self.current,
        })

        if self._captureless:  # no imagery captured with this job
            self.total = 0
            self.remaining = 0
            self.job_ends_after = time.time() + self.duration

            self.status = 'running'
            self.logger.info('starting captureless wait period')

        else:  # we are capturing imagery with this job
            self.logger.info("Asking server to create new CJR for XP_{}.".format(self.xp_id))
            response = requests.post(CJR_NEW_URL, auth=(
                fishface_server_auth.USERNAME,
                fishface_server_auth.PASSWORD
            ), data=payload)
            self.cjr_id = response.json()['cjr_id']
            self._set_name(self.name[:-10] + str(self.cjr_id))
            self.logger.info('Preparing capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))

            first_capture_at = self.start_timestamp + self.startup_delay

            number_of_images_to_capture = int(float(self.duration) / self.interval)

            self.capture_times = [first_capture_at + (j * self.interval) for j in range(number_of_images_to_capture)]

            self.job_ends_after = self.capture_times[-1]
            self.total = len(self.capture_times)
            self.remaining = len(self.capture_times)

            eph_list = [t - self.start_timestamp for t in [self.start_timestamp, self.job_ends_after, time.time()]]
            logger.debug('EPH: start {} stop {} from_now {}'.format(*eph_list))
            logger.debug('EPH: images_to_capture {} interval {} total seconds {}'.format(
                number_of_images_to_capture, self.interval, number_of_images_to_capture * self.interval
            ))

        self.set_ready()

    def _post_run(self):
        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

        if not self._captureless:
            deathcry = self.get_status_dict()
            deathcry['command'] = 'job_status_update'

            logger.debug("publishing deathcry of thread {}".format(self.name))
            self.publish_deathcry(deathcry)

    def _job_without_capture(self):
        # We don't need to do anything periodically except check to see if the job has been
        # aborted, and that is handled by the RegisteredThreadWithHeartbeat class.
        pass

    def _job_with_capture(self):

        self.status = 'running'

        for i, next_capture_time in enumerate(self.capture_times):
            self.beat_heart()

            if time.time() - next_capture_time > 5:
                self.close_camera()
                delay_until(next_capture_time - 4)
                self.open_camera()
            else:
                self.open_camera()

            delay_until(next_capture_time)
            if not self._keep_looping:
                break

            logger.debug('telling server to post XP_{}_CJR_{} data image'.format(
                self.xp_id, self.cjr_id))
            self.controller.imagery_server.post_image_to_server({
                'command': 'post_image',
                'xp_id': self.xp_id,
                'is_cal_image': 0,
                'cjr_id': self.cjr_id,
                'voltage': self.voltage,
                'current': self.current,
                'species': self.species,
            })

            self.remaining = self.total - i - 1

        # We handled the heartbeat stuff manually above, so no need to have the
        # RegisteredThreadWithHeartbeat class do its own looping.
        self._keep_looping = False

    def abort_job(self):
        self._keep_looping = False
        self.logger.info('Job aborted: {}'.format(self.get_status_dict()))
        self.status = 'aborted'

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


class DeathcryPublisher(RegisteredThreadWithHeartbeat):
    def __init__(self,
                 post_method, thread_registry,
                 *args, **kwargs):
        super(DeathcryPublisher, self).__init__(
            name='deathcry_publisher',
            thread_registry=thread_registry,
            heartbeat_interval=0.3,
            *args, **kwargs)

        self.deathcries = Queue.Queue()
        self.post_method = post_method

    def _heartbeat_run(self):
        try:
            self.post_method(self.deathcries.get_nowait())
            self.deathcries.task_done()
        except Queue.Empty:
            pass

    def add_deathcry(self, deathcry):
        self.deathcries.put(deathcry)


class CaptureJobController(RegisteredThreadWithHeartbeat):
    def __init__(self,
                 imagery_server,
                 thread_registry,
                 *args, **kwargs):
        super(CaptureJobController, self).__init__(thread_registry=thread_registry,
                                                   heartbeat_interval=0.5,
                                                   name='capturejob_controller',
                                                   *args, **kwargs)
        self.imagery_server = imagery_server

        self.logger = logging.getLogger('raspi.capturejob_controller')
        self.logger.setLevel(logging.DEBUG)

        self._queue = list()
        self._current_job = None
        self._staged_job = None

        self.deathcry_publisher = DeathcryPublisher(
            post_method=self.imagery_server.telemeter.post_to_fishface,
            thread_registry=self._thread_registry
        )
        self.deathcry_publisher.start()
        self.publish_deathcry = self.deathcry_publisher.add_deathcry

        self._deathcries = Queue.Queue()


    def _pre_run(self):
        if_threads_do_not_start_abort_at = time.time() + 10

        threads_to_wait_for = [
            'deathcry_publisher',
        ]

        logger.info('CJC is waiting for the threads it depends on to be ready: ' +
                    '{} and httpd.'.format(str(threads_to_wait_for)))

        waiting_for_threads = list()
        for thr in self._thread_registry:
            if thr.name in threads_to_wait_for:
                waiting_for_threads.append(thr)

        if not waiting_for_threads:
            logger.error("No threads found to watch.")
            raise Exception("Can't find threads to watch.")

        logger.debug("waiting for: {}".format(str([thr.name for thr in waiting_for_threads])))

        while time.time() < if_threads_do_not_start_abort_at:
            if (self.imagery_server._httpd_soon_to_be_ready and
                    all([thr.ready for thr in waiting_for_threads])):
                break
            delay_for_seconds(0.1)
        else:
            logger.error('Threads that the CJC depend on did not report readiness. Aborting.')
            self.imagery_server.abort()

        self.logger.info('Threads ready; CaptureJob Controller starting up.')

    def _heartbeat_run(self):
        #
        # Primary CJC loop handler.
        #

        keep_camera_open = True

        if self._current_job is not None:
            self.logger.debug('Reporting on current job.')
            current_status = self.get_current_job_status()
            if current_status['cjr_id'] is not None:
                current_status['command'] = 'job_status_update'
                self.imagery_server.telemeter.post_to_fishface(current_status)

            if self._current_job.status == 'aborted' or (
                        self._current_job.job_ends_after is not None and
                            self._current_job.job_ends_after < time.time()):
                self.logger.info("Current job is dead or expired; clearing it.")
                self._current_job = None
                delay_until_next_loop = 0.2
            elif self._queue and self._staged_job is None and self._current_job.job_ends_in < 10:
                self.logger.info("Current job ends soon; promoting queued job to staged job.")
                self._staged_job = CaptureJob(self,
                    thread_registry=self.imagery_server.thread_registry,
                    open_camera_method=self.imagery_server.open_camera,
                    close_camera_method=self.imagery_server.close_camera,
                    **self._queue.pop(0)
                )

        else:  # there is no current job
            if self._staged_job is not None:  # there is a staged job
                self.logger.info('Promoting staged job.')
                self._current_job = self._staged_job
                self._current_job.start()
                self._staged_job = None
            else:  # there is no staged job
                if self._queue:  # there are jobs in queue
                    self.logger.info('No jobs active or staged, but jobs in queue.')
                    self._current_job = CaptureJob(self,
                        thread_registry=self.imagery_server.thread_registry,
                        open_camera_method=self.imagery_server.open_camera,
                        close_camera_method=self.imagery_server.close_camera,
                        **self._queue.pop(0)
                    )
                    self._current_job.start()
                    self.logger.debug('Started new current job.')

                else:  # queue is empty
                    keep_camera_open = False
                    if self.imagery_server.power_supply.output:
                        self.logger.info('Shutting down power supply until the next job arrives.')
                        self.set_psu({
                            'voltage': 0,
                            'current': 0,
                            'enable_output': 0,
                        })

        if keep_camera_open:
            if self.imagery_server.camera is None:
                self.imagery_server.open_camera()
        else:
            if self.imagery_server.camera is not None and not self.imagery_server.pending_image_acquisitions:
                logger.info('Shutting down camera until the next job arrives.')
                self.imagery_server.close_camera()

    def get_current_job_status(self):
        return self._current_job.get_status_dict()

    def get_staged_job_status(self):
        return self._staged_job.get_status_dict()

    def abort_running_job(self):
        self.logger.info("Aborting current job.")
        if self._current_job is not None:
            self._current_job.abort_job()

    def abort_all_jobs(self, payload):
        self.logger.info("Aborting all jobs!")
        self._queue = list()
        self._staged_job = None
        self.abort_running_job()
        return payload

    def insert_job(self, job_spec, position):
        self.logger.info('Inserting job at position {} in queue.'.format(position))
        self._queue.insert(position, job_spec)

    def append_job(self, job_spec):
        self.logger.info('Appending job to queue.')
        self.insert_job(len(self._queue), job_spec)

    def set_psu(self, *args, **kwargs):
        self.logger.debug('Passing set_psu request up to the ImageryServer.')
        self.imagery_server.set_psu(*args, **kwargs)

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

    def abort(self):
        logger.info('Shutting down CJC.')
        self.abort_all_jobs(payload=None)
        super(CaptureJobController, self).abort()


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

        self.logger.debug('POST response code: {}'.format(response.status_code))

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


class ThreadedHTTPServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn):
    pass


class ImageryServer(object):
    """
    """

    def __init__(self):
        self.thread_registry = list()
        self.telemeter = Telemeter(imagery_server=self)

        if REAL_HARDWARE:
            self.power_supply = RobustPowerSupply.RobustPowerSupply()
        else:
            self.power_supply = ik.HP6652a()

        self.server_address = (HOST, PORT)
        self.httpd = ThreadedHTTPServer(
            self.server_address,
            CommandHandler
        )
        self.httpd.parent = self
        self._httpd_soon_to_be_ready = False

        self.capturejob_controller = CaptureJobController(imagery_server=self,
                                                          thread_registry=self.thread_registry)
        self.capturejob_controller.start()

        self.power_supply.output = False
        self.power_supply.current = 0
        self.power_supply.voltage = 0

        self.pending_image_acquisitions = 0
        self.pending_image_acquisitions_lock = threading.Lock()

        self.camera = None
        self.camera_lock = threading.Lock()


        self._job_status = None
        self.httpd_server_starting = True

        self.command_dispatch = {
            'set_psu': self.set_psu,
            'post_image': self.post_image_to_server,
            'post_calibration_image': self.post_calibration_image,

            'insert_job': self.capturejob_controller.insert_job,
            'job_status': self.capturejob_controller.complete_status,

            'set_queue': self.capturejob_controller.set_queue,

            'abort_running_job': self.capturejob_controller.abort_running_job,
            'abort_all': self.capturejob_controller.abort_all_jobs,

            'raspi_monitor': self.monitor,
        }

    def open_camera(self, resolution=(2048, 1536), rotation=180):
        with self.camera_lock:
            if self.camera is None:
                open_camera_start = time.time()
                self.camera = picamera.PiCamera()
                self.camera.resolution = resolution
                self.camera.rotation = rotation
                logger.info('camera open in {} seconds'.format(time.time() - open_camera_start))

    def close_camera(self):
        if not self.pending_image_acquisitions:
            with self.camera_lock:
                if self.camera is not None:
                    if not self.camera.closed:
                        self.camera.close()
                    self.camera = None
                logger.debug('camera is closed')

    def post_image_to_server(self, payload):
        with self.pending_image_acquisitions_lock:
            self.pending_image_acquisitions += 1

        if self.camera is None or self.camera.closed:
            logger.warning('Tried to capture with closed camera.  Opening camera on the fly.')
            self.open_camera()

        stream = io.BytesIO()
        with self.camera_lock:
            capture_time = float(time.time())
            self.camera.capture(stream, format='jpeg')

        with self.pending_image_acquisitions_lock:
            self.pending_image_acquisitions -= 1

        logger.debug('image took {} seconds to acquire from camera'.format(
            float(time.time()) - capture_time
        ))

        voltage = self.power_supply.voltage_sense
        current = self.power_supply.current_sense
        logger.debug('power supply measurements acquired')

        image_dtg = datetime.datetime.fromtimestamp(capture_time).strftime(DATE_FORMAT)

        image_filename = 'XP-{}_CJR-{}_{}_{}_{}.jpg'.format(
            payload['xp_id'],
            payload['cjr_id'],
            payload['species'],
            image_dtg,
            capture_time,
        )

        logger.debug('posting image {}'.format(image_filename))

        is_cal_image = (str(payload['is_cal_image']).lower()
                        in ['true', 't', 'yes', 'y', '1'])

        payload['filename'] = image_filename
        payload['capture_time'] = capture_time
        payload['voltage'] = float(voltage)
        payload['current'] = float(current)
        payload['is_cal_image'] = str(is_cal_image)

        stream.seek(0)
        files = {image_filename: stream}

        image_start_post_time = time.time()
        result = self.telemeter.post_to_fishface(payload=payload, files=files)
        logger.info(result)
        logger.info("image {} posted in {} seconds".format(payload['filename'],
                                                           time.time() - image_start_post_time))

        return payload

    def post_calibration_image(self, payload):
        if self.power_supply.output:
            self.power_supply.output = False
            delay_for_seconds(5)

        payload.update({
            'command': "post_image",
            'is_cal_image': 1,
            'cjr_id': 0,
        })

        reply = self.post_image_to_server(payload)

        return reply

    def async_image_post(self, payload):
        logger.debug('preparing to post image asynchronously')
        payload['async'] = True
        async_thread = threading.Thread(
            name="async_image_post_thread",
            target=self.post_image_to_server,
            args=(payload,)
        )
        async_thread.start()

        return payload

    def monitor(self, payload):
        response = {
            'command': 'raspi_monitor',
            'psu_voltage_meas': round(float(self.power_supply.voltage_sense), 3),
            'psu_current_meas': round(float(self.power_supply.current_sense), 3),
        }

        response['threads'] = [{
            'name': thr.name,
            'delta': thr.last_heartbeat_delta,
            'last': thr.last_heartbeat,
        } for thr in self.thread_registry]

        return response

    def run(self):

        logger.info("starting http server thread")

        self._httpd_soon_to_be_ready = True
        self.httpd.serve_forever()

    def abort(self):
        for thr in self.thread_registry:
            thr.abort()

        self.httpd.server_close()

    def set_psu(self, payload):
        if bool(int(payload.get('reset', False))):
            self.power_supply.voltage = 0
            self.power_supply.current = 0
            self.power_supply.output = False
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
        else:
            self.power_supply.voltage = 0

        if current:
            logger.debug("setting psu max current to {} A".format(
                current
            ))
            self.power_supply.current = current
        else:
            self.power_supply.current = 0

        if enable_output:
            logger.debug("enabling psu output")
        else:
            logger.debug("disabling psu output")

        self.power_supply.output = enable_output

        thread = threading.Thread(
            name='posting_psu_sensed_data',
            target=self.post_power_supply_sensed_data,
            args=(payload, 1,)
        )
        thread.start()

        return False

    def post_power_supply_sensed_data(self, payload, delay=None):
        if delay is not None:
            time.sleep(delay)
        payload['command'] = 'power_supply_log'

        payload['voltage_meas'] = float(self.power_supply.voltage_sense)
        payload['current_meas'] = float(self.power_supply.current_sense)

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

    def log_message(self, format_string, *args):
        if 'POST /telemetry/ HTTP/1.1' not in args:
            logger.warning(format_string, *args)
        else:
            logger.debug(format_string, *args)


def main():
    logger.info("Starting Raspi unprivileged server.")

    imagery_server = ImageryServer()

    try:
        imagery_server.run()
    except KeyboardInterrupt:
        imagery_server.abort()

    logger.info("Exiting Raspi unprivileged server.")

    force_exit_at = time.time() + 3
    while time.time() < force_exit_at:
        if threading.active_count() == 1:
            break
        delay_for_seconds(0.1)
    else:
        logger.error("Not all non-main threads died when they were supposed to: {}".format(
            [thr.name for thr in threading.enumerate()]
        ))
        sys.exit()


if __name__ == '__main__':
    main()
