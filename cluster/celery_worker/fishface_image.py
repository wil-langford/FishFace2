import numpy as np

NORMALIZED_SHAPE = (384, 512)
NORMALIZED_DTYPE = np.uint8


class FFImage(object):
    def __init__(self, input_array=None, meta=None, log=None):
        if input_array is None:
            self.array = np.zeros(NORMALIZED_SHAPE, dtype=NORMALIZED_DTYPE)
        elif not isinstance(input_array, np.ndarray):
            raise InvalidSourceArray('If specified, input_array must be a numpy array.')
        elif input_array.shape != NORMALIZED_SHAPE or input_array.dtype != NORMALIZED_DTYPE:
            raise InvalidSourceArray('input_array must have shape {} and dtype {}.'.format(
                NORMALIZED_SHAPE, NORMALIZED_DTYPE))
        else:
            self.array = input_array

        self.meta = meta
        self._log = log

        if self.meta is None:
            self.meta = dict()

        if self._log is None:
            self._log = list()


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


class InvalidSourceArray(Exception):
    pass