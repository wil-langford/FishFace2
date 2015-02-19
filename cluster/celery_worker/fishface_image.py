import os
import sys

import numpy as np
import cv2
import cv2.cv as cv
import functools

NORMALIZED_SHAPE = (384, 512)
NORMALIZED_DTYPE = np.uint8


def ff_operation(func):
    @functools.wraps(func)
    def wrapper(ff_image, *args, **kwargs):
        fname = func.__name__
        ff_image.log = 'OP: {}'.format(fname)

        if not isinstance(ff_image, FFImage):
            raise TypeError('{} requires an FFImage object as its first argument.'.format(fname))

        ff_image.array = func(ff_image.array, *args, ff_image=ff_image, **kwargs)
        return ff_image

    return wrapper


def ff_annotation(func):
    @functools.wraps(func)
    def wrapper(ff_image, *args, **kwargs):
        fname = func.__name__
        ff_image.log = 'AN: {}'.format(fname)

        if not isinstance(ff_image, FFImage):
            raise TypeError('{} requires an FFImage object as its first argument.'.format(fname))

        func(ff_image.array, *args, ff_image=ff_image, **kwargs)
        return ff_image

    return wrapper


def array_to_jpeg_string(arr, quality=90):
    retval, jpeg_string = cv2.imencode('.jpg', arr, (cv2.IMWRITE_JPEG_QUALITY, quality))
    return jpeg_string.tostring()


def jpeg_string_to_array(jpeg_string):
    if isinstance(jpeg_string, basestring):
        jpeg_array = np.fromstring(jpeg_string, dtype=np.uint8)
    elif isinstance(jpeg_string, np.ndarray):
        jpeg_array = jpeg_string
    else:
        raise InvalidSource('Need string or numpy array, not {}'.format(jpeg_string.__class__))
    return cv2.imdecode(jpeg_array, 0)


def normalize_array(image):
    if image.shape == NORMALIZED_SHAPE:
        return image

    # too many color channels
    if len(image.shape) == 3:
        channels = image.shape[2]
        if channels == 3:
            conversion = cv.CV_BGR2GRAY
        elif channels == 4:
            conversion = cv.CV_BGRA2GRAY
        else:
            raise Exception("Why do I see {} color channels? ".format(channels) +
                            "I can only handle 1, 3, or 4 (with alpha).")

        image = cv2.cvtColor(image, conversion)

    if image.shape != NORMALIZED_SHAPE:
        image = cv2.resize(image,
                           dsize=tuple(reversed(NORMALIZED_SHAPE)),
                           interpolation=cv.CV_INTER_AREA)
    return image


def normalize_jpeg(jpeg_string):
    return array_to_jpeg_string(normalize_array(jpeg_string_to_array(jpeg_string)))


class FFImage(object):
    def __init__(self, source=None, source_filename=None,
                 meta=None, log=None, normalize_image=True):
        jpeg_string = None

        self.meta = meta
        self._log = log

        if self.meta is None:
            self.meta = dict()

        if self._log is None:
            self._log = list()

        if isinstance(source, basestring):
            jpeg_string = source

        if jpeg_string is None and source_filename is not None:
            if os.path.isfile(source_filename):
                with open(source_filename, 'rb') as jpeg_file:
                    jpeg_string = jpeg_file.read()
                self.meta['filename'] = source_filename

        if jpeg_string is None and isinstance(source, np.ndarray):
            if not normalize_image and (source.shape != NORMALIZED_SHAPE or
                                        source.dtype != NORMALIZED_DTYPE):
                raise InvalidSource('input_array must have shape {} and dtype {}.'.format(
                    NORMALIZED_SHAPE, NORMALIZED_DTYPE))

            jpeg_string = array_to_jpeg_string(source)

        if jpeg_string is None and source is not None:
            raise Exception('None of the provided sources were usable.  Need a jpeg filename' +
                            'string, a raw jpeg as a string, or a numpy array image.')

        if jpeg_string is None:
            jpeg_string = array_to_jpeg_string(np.zeros(NORMALIZED_SHAPE, dtype=NORMALIZED_DTYPE))

        if normalize_image and jpeg_string is not None:
            jpeg_string = normalize_jpeg(jpeg_string)

        self.jpeg_string = jpeg_string
        self._array = None

    @property
    def log(self):
        return self._log

    @log.setter
    def log(self, item):
        self._log.append(item)

    @property
    def height(self):
        return self.array.shape[0]

    @property
    def width(self):
        return self.array.shape[1]

    def write_file_to_dir(self, dir_path):
        full_path = os.path.join(dir_path, self.meta['filename'])
        with open(full_path, 'wb') as write_file:
            write_file.write(self.jpeg_string)

    @property
    def array(self):
        if self._array is None:
            self._array = jpeg_string_to_array(self.jpeg_string)
        return self._array

    @array.setter
    def array(self, arr):
        self.jpeg_string = array_to_jpeg_string(arr)
        self._array = arr

    def sanitize(self):
        self._array = None
        del self.meta['all_contours']

    @property
    def approximate_memory_usage(self):
        """
        Quick and super extra really dirty.
        """
        total = dict()
        if self._array is not None:
            total['array'] = self._array.nbytes
        total['jpeg_string'] = sys.getsizeof(self.jpeg_string)
        total['meta'] = sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in self.meta.iteritems())
        total['log'] = sum(sys.getsizeof(v) for v in self._log)

        return sum(total.itervalues()), total

class InvalidSource(Exception):
    pass