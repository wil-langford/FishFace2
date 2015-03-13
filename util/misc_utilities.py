import time
import logging


def delay_until(unix_timestamp):
    now = time.time()
    while now < unix_timestamp:
        time.sleep(unix_timestamp - now)
        now = time.time()


def delay_for_seconds(seconds):
    later = time.time() + seconds
    delay_until(later)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def return_text_file_contents(file_path, strip=True):
    try:
        with open(file_path, 'rt') as f:
            if strip:
                return f.read().strip()
            else:
                return f.read()
    except IOError:
        logging.warning("Couldn't read file: {}".format(file_path))