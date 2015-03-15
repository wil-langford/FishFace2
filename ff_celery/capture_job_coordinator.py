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


@celery.shared_task(name='cjc.set_queue')
def set_queue(**kwargs):
    ecc.set_queue(**kwargs)


class CaptureJob(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, startup_delay, interval, duration, voltage, current,
                 xp_id, species,
                 *args, **kwargs):
        super(CaptureJob, self).__init__()

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

        logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup_delay'

        celery_app.send_task('set_psu', kwargs={
            'enable_output': bool(self.voltage),
            'voltage': self.voltage,
            'current': self.current,
        })

        logger.info("Asking server to create new CJR for XP_{}.".format(self.xp_id))
        r_cjr_id = celery_app.send_task('results.new_cjr', args=(
            self.xp_id, self.voltage, self.current, self.start_timestamp))

        self.cjr_id = r_cjr_id.get(timeout=ff_conf.CJR_CREATION_TIMEOUT)

        self._set_name(self.name[:-10] + str(self.cjr_id))
        logger.info('Preparing capture for XP_{}_CJR_{}'.format(self.xp_id, self.cjr_id))

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

        celery_app.send_task('results.job_status_update', self.get_status_dict())

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
        logger.info('Job aborted: {}'.format(self.get_status_dict()))
        self.status = 'aborted'
        self.post_report()

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

    def post_report(self):
        celery_app.send_task('results.job_status_report', kwargs=self.get_status_dict())


class NonCaptureJob(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, duration, voltage, current, start_timestamp=None,
                 *args, **kwargs):
        super(NonCaptureJob, self).__init__()

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

        self.start_timestamp = start_timestamp
        self.stop_timestamp = None

    def _pre_run(self):
        self.start_timestamp = self.start_timestamp if self.start_timestamp else time.time()

        delay_until(self.start_timestamp)

        logger.info("starting up job for experiment {}".format(self.xp_id))
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
        logger.info('starting captureless wait period')

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
        logger.info('Job aborted: {}'.format(self.get_status_dict()))
        self.status = 'aborted'
        self.post_report()

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

    def post_report(self):
        # no need to send updates on what is basically a static job after it starts
        pass


class ExperimentCaptureController(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, *args, **kwargs):
        super(ExperimentCaptureController, self).__init__(*args, **kwargs)

        self.job_queue = list()
        self._job_queue_lock = threading.RLock()

        self.current_job = None
        self.staged_job = None

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

        self.job_queue = queue

        return True

    def complete_status(self):
        return {
            'current_job': self.current_job if self.current_job else None,
            'staged_job': self.staged_job if self.staged_job else None,
            'queue': self._job_queue if self._job_queue else [],
        }

    def abort_all(self):
        if self.job_queue:
            self.job_queue = list()
        if self.staged_job is not None:
            self.staged_job = None
        if self.current_job is not None:
            self.current_job.abort_job()

            self.current_job = None

        celery_app.send_task('camera.abort').get(timeout=1)
        celery_app.send_task('psu.reset_psu')

    def _heartbeat_run(self):
        # there is no currently running job
        if self.current_job is None:
            if self.staged_job is not None:  # there is a staged job
                logger.info('Promoting staged job.')
                self.current_job = self.staged_job
                self.current_job.start()
                self.staged_job = None
            else:  # there is no staged job
                if self.job_queue:  # there are jobs in queue
                    logger.info('No jobs active or staged, but jobs in queue.')
                    next_job = self.queue.pop(0)
                    if next_job['interval'] > 0:
                        self.current_job = CaptureJob(self, **next_job)
                    else:
                        self.current_job = NonCaptureJob(self, **next_job)
                    self.current_job.start()
                    logger.debug('Started new current job.')

                else:  # queue is empty
                    if self.imagery_server.power_supply.output:
                        logger.info('Shutting down power supply until the next job arrives.')
                        self.set_psu({
                            'voltage': 0,
                            'current': 0,
                            'enable_output': 0,
                        })

        # there is a currently running job
        else:
            self.logger.debug('Reporting on current job.')
            self.current_job.post_report()
            current_state = self.current_job.get_status_dict()

            if current_state['status'] == 'aborted' or (
                self.current_job.job_ends_after is not None and
                self.current_job.job_ends_after < time.time()):
                self.logger.info("Current job is dead or expired; clearing it.")
                self.current_job = None
            elif self.job_queue and self.staged_job is None and self.current_job.job_ends_in < 10:
                self.logger.info("Current job ends soon; promoting queued job to staged job.")
                next_job = self.queue.pop(0)
                if next_job['interval'] > 0:
                    self.staged_job = CaptureJob(self, **next_job)
                else:
                    self.staged_job = NonCaptureJob(self, **next_job)
