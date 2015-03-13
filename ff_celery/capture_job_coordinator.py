import threading
import time

import celery
import redis

from util import thread_with_heartbeat
from ff_celery.fishface_celery import celery_app

from util.misc_utilities import delay_until

import util.fishface_config as ff_conf

from util.fishface_logging import logger

thread_registry = thread_with_heartbeat.ThreadRegistry()

ecc = None
redis_client = redis.Redis(
    host=ff_conf.REDIS_HOSTNAME,
    password=ff_conf.REDIS_PASSWORD
)


@celery.shared_task(bind=True, name='cjc.debug_task')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@celery.shared_task(name='cjc.thread_heartbeat')
def thread_heartbeat(*args, **kwargs):
    global thread_registry
    thread_registry.receive_heartbeat(*args, **kwargs)


@celery.shared_task(name='cjc.queues_length')
def queues_length(queue_list=None):
    global redis_client
    if queue_list is None:
        queue_list = ff_conf.CELERY_QUEUE_NAMES
    elif isinstance(queue_list, basestring):
        queue_list = [queue_list]

    return [(queue_name, redis_client.llen(queue_name)) for queue_name in queue_list]


@celery.shared_task(name='cjc.complete_status')
def complete_status():
    global ecc
    return ecc.complete_status()


class CaptureJob(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, startup_delay, interval, duration, voltage, current,
                 xp_id, species,
                 *args, **kwargs):
        super(CaptureJob, self).__init__(*args, **kwargs)

        self.status = 'staged'

        self.startup_delay = float(startup_delay)
        self.interval = float(interval)
        self.duration = float(duration)
        self.voltage = float(voltage)
        self.current = float(current)

        self.xp_id = int(xp_id)
        self.cjr_id = None
        self.species = str(species)

        self.name = 'XP_{}_CJR_pending_id'.format(self.xp_id)

        self.total = None
        self.remaining = None

        self.capture_times = None
        self.job_ends_after = None

        self.start_timestamp = None
        self.stop_timestamp = None

    def _pre_run(self):
        self.start_timestamp = time.time()

        self.logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup_delay'

        celery_app.send_task('set_psu', kwargs={
            'enable_output': bool(self.voltage),
            'voltage': self.voltage,
            'current': self.current,
        })

        self.logger.info("Asking server to create new CJR for XP_{}.".format(self.xp_id))
        r_cjr_id = celery_app.send_task('results.new_cjr', args=(
            self.xp_id, self.voltage, self.current, self.start_timestamp))

        self.cjr_id = r_cjr_id.get(timeout=ff_conf.CJR_CREATION_TIMEOUT)

        self._set_name(self.name[:-10] + str(self.cjr_id))
        self.logger.info('Preparing capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))

        first_capture_at = self.start_timestamp + self.startup_delay

        self.capture_times = [first_capture_at + (j * self.interval)
                              for j in range(int(float(self.duration) / self.interval))]

        self.job_ends_after = self.capture_times[-1]
        self.total = len(self.capture_times)
        self.remaining = self.total

        self.set_ready()

    def _post_run(self):
        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

        celery_app.send_task('results.cjr_deathcry', self.get_status_dict())

    def _heartbeat_run(self):
        self.status = 'running'

        meta = {
            'cjr_id': self.cjr_id,
            'is_cal_image': False,
            'voltage': self.voltage,
            'current': self.current,
        }

        for i, next_capture_time in enumerate(self.capture_times):
            self.beat_heart()

            delay_until(next_capture_time - ff_conf.CAMERA_QUEUE_PRELOAD)
            if not self._keep_looping:
                break

            celery_app.send_task('camera.queue_capture_request',
                                 args=(next_capture_time, meta))

            self.remaining = self.total - i - 1

        # We handled the heartbeat stuff manually above, so no need to have the
        # ThreadWithHeartbeat class do its own looping.
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


class NonCaptureJob(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, duration, voltage, current, *args, **kwargs):
        super(NonCaptureJob, self).__init__(*args, **kwargs)

        self.status = 'staged'

        self.duration = float(duration)
        self.voltage = float(voltage)
        self.current = float(current)

        self.name = 'job_without_capture_{}_seconds_at_{}_volts'.format(
            self.duration, self.voltage
        )
        self._heartbeat_interval = 0

        self.cjr_id = None

        self.total = None
        self.remaining = None

        self.capture_times = None
        self.job_ends_after = None

        self.start_timestamp = None
        self.stop_timestamp = None

    def _pre_run(self):
        self.start_timestamp = time.time()

        self.logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup'

        self.controller.set_psu({
            'enable_output': bool(self.voltage),
            'voltage': self.voltage,
            'current': self.current,
        })

        self.total = 0
        self.remaining = 0
        self.job_ends_after = time.time() + self.duration

        self.status = 'running'
        self.logger.info('starting captureless wait period')

        self.set_ready()

    def _post_run(self):
        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

    def _heartbeat_run(self):
        # We don't need to do anything periodically except check to see if the job has been
        # aborted, and that is handled by the ThreadWithHeartbeat class.
        pass

    def abort_job(self):
        self._keep_looping = False
        self.logger.info('Job aborted: {}'.format(self.get_status_dict()))
        self.status = 'aborted'

    def get_status_dict(self):
        return {
            'status': self.status,
            'xp_id': 0,
            'cjr_id': self.cjr_id,
            'species': 0,
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


class ExperimentCaptureController(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, *args, **kwargs):
        super(ExperimentCaptureController, self).__init__(*args, **kwargs)

        self.job_queue = list()
        self._job_queue_lock = threading.RLock()

        self.current_cjr = None

        self._complete_status = None

        self.command_dispatch = {
            'abort_running_job': self.capturejob_controller.abort_running_job,
            'abort_all': self.capturejob_controller.abort_all_jobs,

            'raspi_monitor': self.monitor,
        }

    def set_queue(self, xp_id, species, queue):
        for job in queue:
            job['xp_id'] = xp_id
            job['species'] = species

        self._job_queue = queue

        return True

    def complete_status(self):
        return {
            'current_job': self.current_cjr if self.current_cjr else None,
            'queue': self._job_queue if self._job_queue else [],
        }