import time
import logging
import os
import celery.result as cel_res
import celery.exceptions as cel_ex
import numpy as np
import cv2


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


def return_text_file_contents(file_path, strip=True, ignore_fail=True):
    try:
        with open(file_path, 'rt') as f:
            if strip:
                return f.read().strip()
            else:
                return f.read()
    except IOError:
        if not ignore_fail:
            logging.warning("Couldn't read file: {}".format(file_path))
        return ''


def chunkify(chunkable, chunk_length=1):
    while chunkable:
        chunk = chunkable[:chunk_length]
        chunkable = chunkable[chunk_length:]
        yield chunk


def is_file(*args):
    return os.path.isfile(os.path.join(*args))


def n_chunkify(n, chunkable):
    """
    Split chunkable into (roughly) n chunks.
    """
    chunk_length = float(len(chunkable)) / n
    for i in xrange(0, n-1):
        start = int(i*chunk_length)
        stop = int((i+1)*chunk_length)
        yield chunkable[start:stop]
    yield chunkable[int((n-1)*chunk_length):]


def image_string_to_array(image_string):
    if isinstance(image_string, basestring):
        image_array = np.fromstring(image_string, dtype=np.uint8)
    elif isinstance(image_string, np.ndarray):
        image_array = image_string
    else:
        raise Exception('Need string or numpy array, not {}'.format(image_string.__class__))
    return cv2.imdecode(image_array, 0)
