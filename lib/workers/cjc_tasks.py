import threading
import time

import celery
# from celery.exceptions import TimeoutError
import redis

import lib.thread_with_heartbeat as thread_with_heartbeat
from lib.fishface_celery import celery_app

from lib.misc_utilities import delay_until

import etc.fishface_config as ff_conf

from lib.fishface_logging import logger

thread_registry = thread_with_heartbeat.ThreadRegistry()

ecc = None
redis_client = redis.Redis(
    host=ff_conf.REDIS_HOSTNAME,
    password=ff_conf.REDIS_PASSWORD
)


def ensure_ecc():
    global ecc
    if ecc is None or not ecc.is_alive():
        ecc_ready_event = threading.Event()
        ecc = ExperimentCaptureController(startup_event=ecc_ready_event)
        ecc.start()
        ecc_ready_event.wait(timeout=5)


@celery.shared_task(name='cjc.ping')
def ping():
    return True


@celery.shared_task(bind=True, name='cjc.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


@celery.shared_task(name='cjc.thread_states')
def thread_states():
    global thread_registry
    return thread_registry.thread_states


@celery.shared_task(name='cjc.thread_registry')
def thread_states():
    global thread_registry
    return thread_registry.registry


@celery.shared_task(name='cjc.thread_heartbeat')
def thread_heartbeat(name, timestamp, count, final=False):
    global thread_registry


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
    if ecc is None or not ecc.is_alive():
        return {
            'current_job': None,
            'staged_job': None,
            'queue': [],
        }
    else:
        return ecc.complete_status()


@celery.shared_task(name='cjc.abort_all')
def abort_all():
    global ecc
    if ecc is None or not ecc.is_alive():
        return True
    else:
        return ecc.abort_all()


@celery.shared_task(name='cjc.queues_ping')
def queues_ping():
    return [(queue_name, celery_app.send_task(queue_name + '.ping'))
            for queue_name in ff_conf.CELERY_QUEUE_NAMES]


@celery.shared_task(name='cjc.monitor')
def monitor():
    return celery.group([celery.signature('results.get_result_cache'), celery.signature('cjc.queues_ping')])()


@celery.shared_task(name='cjc.cjr_id_catcher')
def cjr_id_catcher(start_timestamp, cjr_id):
    global ecc
    capturejob = ecc.current_job

    if capturejob.start_timestamp == start_timestamp:
        capturejob.cjr_id = int(cjr_id)
        capturejob.name = capturejob.name[:-10] + str(capturejob.cjr_id)
        capturejob.cjr_id_event.set()
        return capturejob.name
    else:
        logger.error('Failed to set CJR id for current job.')
        return False


@celery.shared_task(name='cjc.set_queue')
def set_queue(xp_id, species, queue):
    global ecc
    ensure_ecc()
    return ecc.set_queue(xp_id, species, queue)


class CaptureJob(thread_with_heartbeat.ThreadWithHeartbeat):
    def __init__(self, startup_delay, interval, duration, voltage, current,
                 xp_id, species):
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

        self.cjr_id_event = threading.Event()

    def _pre_run(self):
        self.start_timestamp = time.time()
        first_capture_at = self.start_timestamp + self.startup_delay

        logger.info("starting up job for experiment {}".format(self.xp_id))
        self.status = 'startup_delay'

        celery_app.send_task('set_psu', kwargs={
            'enable_output': bool(self.voltage),
            'voltage': self.voltage,
            'current': self.current,
        })

        logger.info("Asking server to create new CJR for XP_{}.".format(self.xp_id))
        r_cjr_id = (
            celery_app.signature('results.new_cjr',
                                 kwargs={
                                     'xp_id': self.xp_id,
                                     'voltage': self.voltage,
                                     'current': self.current,
                                     'start_timestamp': self.start_timestamp
                                 }) |
            celery_app.signature('cjc.cjr_id_catcher')
        ).apply_async()

        logger.info('Preparing list of captures.'.format(self.xp_id, self.cjr_id))

        self.capture_times = [first_capture_at + (j * self.interval)
                              for j in range(int(float(self.duration) / self.interval))]

        self.job_ends_after = self.capture_times[-1]
        self.total = len(self.capture_times)
        self.remaining = self.total

        logger.error('REMAINING / TOTAL = {} / {}'.format(self.remaining, self.total))

        self.set_ready()
        # Abort if we don't have a CJR id at least 1 second before we're supposed to
        # start capturing.
        if not self.cjr_id_event.wait(timeout=first_capture_at - time.time() - 1):
            self.abort()
            logger.error('Could not get CJR id from server. Aborting!')

    def _post_run(self):
        self.stop_timestamp = time.time()
        if self.status == 'running':
            self.status = 'completed'

        celery_app.send_task('results.job_status_report', kwargs=self.get_status_dict())

    def _heartbeat_run(self):
        self.status = 'running'
        logger.error('REMAINING / TOTAL = {} / {}'.format(self.remaining, self.total))

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
                                 kwargs={
                                     'requested_capture_timestamp': next_capture_time,
                                     'meta': meta,
                                 })

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
            'remaining': self.remaining if self.remaining else 0,
            'total': self.total if self.total else 0,
            'voltage': self.voltage,
            'current': self.current,
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
    def __init__(self, duration, voltage, current, start_timestamp=None):
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
            'species': 0,
            'voltage': self.voltage,
            'current': self.current,
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

        self.name = 'ECC'

        self.job_queue = list()
        self._job_queue_lock = threading.RLock()

        self.current_job = None
        self.staged_job = None

        self._complete_status = None

        self._queue_set_event = threading.Event()

    def set_queue(self, xp_id, species, queue):
        for job in queue:
            job['xp_id'] = xp_id
            job['species'] = species

        self.job_queue = queue
        self._queue_set_event.set()

        return self.job_queue

    def complete_status(self):
        return {
            'current_job': self.current_job.get_status_dict() if self.current_job else None,
            'staged_job': self.staged_job.get_status_dict() if self.staged_job else None,
            'queue': self.job_queue if self.job_queue else [],
        }

    def abort_all(self):
        if self.job_queue:
            self.job_queue = list()
        if self.staged_job is not None:
            self.staged_job = None
        if self.current_job is not None:
            self.current_job.abort_job()
            self.current_job = None

        celery_app.send_task('camera.abort')
        celery_app.send_task('psu.reset_psu')

        return True

    def _pre_run(self):
        super(ExperimentCaptureController, self)._pre_run()
        # Give the queue time to get set
        logger.info('Waiting up to 3 seconds for queue to be set initially.')
        if self._queue_set_event.wait(timeout=3):
            logger.info("Initial queue setting complete.  Ready to begin looping.")
        else:
            logger.warning("No initial queue setting.  Aborting ECC.")
            self.abort()

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
                    next_job = self.job_queue.pop(0)
                    if next_job['interval'] > 0:
                        logger.error(str(next_job))
                        self.current_job = CaptureJob(**next_job)
                    else:
                        self.current_job = NonCaptureJob(**next_job)
                    self.current_job.start()
                    logger.debug('Started new current job.')

                else:  # queue is empty
                    logger.info('Shutting down capture controller until the next job arrives.')
                    celery_app.send_task('psu.reset_psu')
                    self.abort(complete=True)

        # there is a currently running job
        else:
            logger.debug('Reporting on current job.')
            self.current_job.post_report()
            current_state = self.current_job.get_status_dict()

            if current_state['status'] == 'aborted' or (
                    self.current_job.job_ends_after is not None and
                    self.current_job.job_ends_after < time.time()):
                logger.info("Current job is dead or expired; clearing it.")
                self.current_job = None
            elif self.job_queue and self.staged_job is None and self.current_job.job_ends_in < 10:
                logger.info("Current job ends soon; promoting queued job to staged job.")
                next_job = self.job_queue.pop(0)
                if next_job['interval'] > 0:
                    self.staged_job = CaptureJob(**next_job)
                else:
                    self.staged_job = NonCaptureJob(**next_job)
