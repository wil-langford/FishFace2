import time
import threading
import collections

from lib.fishface_logging import logger
from lib.fishface_celery import celery_app
from lib.misc_utilities import delay_for_seconds


class ThreadWithHeartbeat(threading.Thread):
    """
    Remember to override the _heartbeat_run(), _pre_run(), and _post_run() methods.
    """

    def __init__(self, heartbeat_interval=0.2, publish_count=None,
                 startup_event=None, *args, **kwargs):
        super(ThreadWithHeartbeat, self).__init__(*args, **kwargs)

        self._name = 'NO_THREAD_NAME_SET'

        self._ready_event = startup_event
        self._heartbeat_log_count = publish_count if publish_count else 1

        self._heartbeat_count = 0
        self._heartbeat_timestamp = None
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_lock = threading.Lock()

        self._keep_looping = True

        self._thread_start_timestamp = time.time()

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
            self.beat_heart()
            self.publish_heartbeat(final=True)

    def set_ready(self):
        logger.info('{} thread reports that it is ready.'.format(self.name))
        if self._ready_event is not None:
            logger.info('Setting startup event per creator request.')
            self._ready_event.set()

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

        if self._heartbeat_log_count is not None:
            if not self._heartbeat_count % self._heartbeat_log_count:
                logger.debug('{} thread heartbeat count is {}'.format(self.name,
                                                                      self._heartbeat_count))
        self.publish_heartbeat()

    def publish_heartbeat(self, final=False):
        with self._heartbeat_lock:
            timestamp, count = self._heartbeat_timestamp, self._heartbeat_count

        celery_app.send_task('cjc.thread_heartbeat', kwargs={
            'name': self.name,
            'timestamp': timestamp,
            'count': count,
            'final': final
        })

    @property
    def heartbeat_count(self):
        return self._heartbeat_count

    @property
    def last_heartbeat(self):
        return self._heartbeat_timestamp

    @property
    def last_heartbeat_delta(self):
        try:
            return time.time() - self._heartbeat_timestamp
        except TypeError:
            return None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        if self._name == 'NO_THREAD_NAME_SET' or 'pending_id' in self._name:
            self._name = new_name + "." + str(time.time())
        else:
            logger.warning("Tried to rename thread.  Thread names are immutable once set.")

    def abort(self, complete=False):
        self._keep_looping = False
        if complete:
            logger.info('Thread {} complete.  Shutting down.'.format(self.name))
        else:
            logger.warning('Thread {} aborted.'.format(self.name))

    @property
    def ready_event(self):
        return self._ready_event

    @property
    def ready(self):
        if self._ready_event is None:
            return True
        else:
            return self._ready_event.is_set()

    @property
    def thread_age(self):
        return time.time() - self._thread_start_timestamp


class ThreadRegistration(object):
    def __init__(self):
        self._timestamp = None
        self._count = 0

    @property
    def state(self):
        return (self._timestamp, self._count)

    def update(self, timestamp, count):
        self._timestamp = timestamp
        self._count = count


class ThreadRegistry(object):
    def __init__(self):
        self._lock = threading.RLock()
        self._registry = collections.defaultdict(ThreadRegistration)

    def receive_heartbeat(self, name, timestamp, count, final=False):
        with self._lock:
            if final:
                try:
                    del self._registry[name]
                except KeyError:
                    pass
            else:
                self._registry[name].update(timestamp, count)

            if final:
                return None
            else:
                return self._registry[name].state


    def thread_state(self, name):
        with self._lock:
            state = self._registry['name'].state

        return (name, state[0], state[1])

    @property
    def thread_list(self):
        with self._lock:
            return self._registry.keys()

    @property
    def thread_states(self):
        with self._lock:
            return [self.thread_state(name) for name in self.thread_list]

    @property
    def registry(self):
        with self._lock:
            return self._registry