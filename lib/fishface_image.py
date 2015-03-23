import os
import sys

import numpy as np
import cv2
import functools

import etc.fishface_config as ff_conf


def ff_operation(func):
    @functools.wraps(func)
    def wrapper(ff_image, *args, **kwargs):
        fname = func.__name__
        ff_image.log = 'OP: {}'.format(fname)

        if 'FFImage' not in str(ff_image.__class__):
            raise TypeError('{} requires an FFImage object as its first argument.'.format(fname))

        ff_image.array = func(ff_image.array, *args, ff_image=ff_image, **kwargs)
        return ff_image

    return wrapper


def ff_annotation(func):
    @functools.wraps(func)
    def wrapper(ff_image, *args, **kwargs):
        fname = func.__name__
        ff_image.log = 'AN: {}'.format(fname)

        if 'FFImage' not in str(ff_image.__class__):
            raise TypeError('{} requires an FFImage object as its first argument.'.format(fname))

        return func(ff_image.array.copy(), *args, ff_image=ff_image, **kwargs)

    return wrapper


def array_to_jpeg_string(arr, quality=90):
    retval, jpeg_string = cv2.imencode('.jpg', arr, (cv2.IMWRITE_JPEG_QUALITY, quality))
    return jpeg_string.tostring()


def image_string_to_array(image_string):
    if isinstance(image_string, basestring):
        image_array = np.fromstring(image_string, dtype=np.uint8)
    elif isinstance(image_string, np.ndarray):
        image_array = image_string
    else:
        raise InvalidSource('Need string or numpy array, not {}'.format(image_string.__class__))
    return cv2.imdecode(image_array, 0)


def array_to_png_string(arr):
    retval, png_string = cv2.imencode('.png', arr)
    return png_string.tostring()


def normalize_array(image):
    if image.shape == ff_conf.NORMALIZED_SHAPE:
        return image

    # too many color channels
    if len(image.shape) == 3:
        channels = image.shape[2]
        if channels == 3:
            conversion = cv2.COLOR_BGR2GRAY
        elif channels == 4:
            conversion = cv2.COLOR_BGRA2GRAY
        else:
            raise Exception("Why do I see {} color channels? ".format(channels) +
                            "I can only handle 1, 3, or 4 (with alpha).")

        image = cv2.cvtColor(image, conversion)

    if image.shape != ff_conf.NORMALIZED_SHAPE:
        image = cv2.resize(image,
                           dsize=tuple(reversed(ff_conf.NORMALIZED_SHAPE)),
                           interpolation=cv2.INTER_AREA)
    return image


def normalize_image_string(image_string):
    return normalize_array(image_string_to_array(image_string))


class FFImage(object):
    def __init__(self, source=None, source_filename=None, source_dir=None,
                 meta=None, log=None,
                 store_source_image_as=None,
                 normalize_image=True):
        image_string = None

        self.meta = meta

        if self.meta is None:
            self.meta = dict()

        if log is None:
            log = list()
        self.meta['log'] = log

        if isinstance(source, basestring):
            image_string = source

        if image_string is None and source_filename is not None:
            if source_dir is not None and os.path.isdir(source_dir):
                source_filename = os.path.join(source_dir, source_filename)
            if os.path.isfile(source_filename):
                with open(source_filename, 'rb') as image_file:
                    image_string = image_file.read()
                self.meta['source_filename'] = os.path.basename(source_filename)
                self.meta['filename'] = self.meta['source_filename']
            else:
                raise InvalidSource("Source file unreadable or non-existent: {}".format(
                    source_filename
                ))

        if image_string is None and isinstance(source, np.ndarray):
            if not normalize_image and (source.shape != ff_conf.NORMALIZED_SHAPE or
                                        source.dtype != ff_conf.NORMALIZED_DTYPE):
                raise InvalidSource('input_array must have shape {} and dtype {}.'.format(
                    ff_conf.NORMALIZED_SHAPE, ff_conf.NORMALIZED_DTYPE))

            image_string = array_to_png_string(source)

        if image_string is None and source is not None:
            raise Exception('None of the provided sources were usable.  Need a jpeg filename' +
                            'string, a raw jpeg as a string, or a numpy array image.')

        if image_string is None:
            image_string = array_to_png_string(np.zeros(ff_conf.NORMALIZED_SHAPE,
                                                        dtype=ff_conf.NORMALIZED_DTYPE))

        if normalize_image and image_string is not None:
            image_array = normalize_image_string(image_string)
            if store_source_image_as is None or store_source_image_as is 'png':
                self.source_image_string = array_to_png_string(image_array)
                self.png_string = self.source_image_string
            else:
                self.source_image_string = array_to_jpeg_string(image_array)
                self.png_string = None
        else:
            self.source_image_string = image_string

        self._array = None
        self._array_clean = True

        if source_filename is None:
            self.meta['source_filename'] = 'IMAGE_NOT_FROM_A_FILE.jpg'

    @property
    def log(self):
        return self.meta['log']

    @log.setter
    def log(self, item):
        self.meta['log'].append(item)

    @property
    def height(self):
        return self.array.shape[0]

    @property
    def width(self):
        return self.array.shape[1]

    def write_file_to_dir(self, dir_path):
        if self.png_string:
            image_string = self.png_string
        else:
            image_string = self.source_image_string
        full_path = os.path.join(dir_path, self.meta['filename'])
        with open(full_path, 'wb') as write_file:
            write_file.write(image_string)

    @property
    def array(self):
        if self._array is None:
            if self.png_string is not None:
                self._array = image_string_to_array(self.png_string)
            else:
                self._array = image_string_to_array(self.source_image_string)

        return self._array

    @array.setter
    def array(self, arr):
        self.png_string = array_to_png_string(arr)
        if self._array_clean:
            self._array_clean = False
            if self.filename.endswith('jpg'):
                self.meta['filename'] = self.filename[:-3] + 'png'
        self._array = arr

    def sanitize(self):
        self._array = None
        del self.meta['all_contours']

    @property
    def filename(self):
        try:
            return self.meta['filename']
        except KeyError:
            return self.meta['source_filename']

    @property
    def approximate_memory_usage(self):
        """
        Quick and super extra really dirty.
        """
        total = dict()
        if self._array is not None:
            total['array'] = self._array.nbytes
        total['jpeg_string'] = sys.getsizeof(self.source_image_string)
        total['png_string'] = sys.getsizeof(self.png_string)
        total['meta'] = sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in self.meta.iteritems())
        total['log'] = sum(sys.getsizeof(v) for v in self.meta['log'])

        return sum(total.itervalues()), total

    @property
    def details(self):
        return_value = list()
        for key, item in self.meta.iteritems():
            if isinstance(item, np.ndarray):
                item_value = "{}: numpy array with shape {}".format(key, item.shape)
            elif key == 'moments':
                item_value = "{}: moments dict with {} entries".format(key, len(item))
            elif key == 'log':
                log_list = ['LOG:']
                log_list.extend(["   " + repr(line) for line in item])
                item_value = '\n'.join(log_list)
            else:
                item_value = "{}: {}".format(key, item)
            return_value.append(item_value)
        return '\n'.join(return_value)


class InvalidSource(Exception):
    pass