"""
"""

import random
import io
import time
import os

import quantities as pq

MAX_VARIANCE_FACTOR = 0.05
HOME_DIR = os.getenv("HOME")
PROJECT_DIR = os.path.join('FishFace2', 'raspi')


class PiCamera(object):
    def __init__(self):
        self.resolution = (2048, 1536)
        self.rotation = 180

        self._closed = False

        with open(os.path.join(HOME_DIR, PROJECT_DIR, "sample-DATA.jpg"), 'rb') as f:
            self._fake_image = f.read()

    def capture(self, stream, format_='jpeg'):
        # shadowing 'format' can't be helped because
        # of the use of it by picamera's capture().
        # plus, isn't Python's 'format' only used on
        # strings?
        if self._closed:
            raise NotImplementedError("Proper errors aren't implemented on fake hardware.")

        if format_ != 'jpeg':
            raise NotImplementedError("Can only fake jpegs currently.")

        if isinstance(stream, io.BytesIO):
            time.sleep(0.2)
            stream.write(self._fake_image)
        else:
            raise Exception("Can only write to io.BytesIO streams.")

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return self._closed


class HP6652a(object):
    """
    Fakes an InstrumentKit power supply well enough to fool FishFace
    during testing.

    >>> fpsu = HP6652a()
    >>> fpsu.voltage
    array(5.0) * V
    >>> abs(fpsu.voltage_sense - fpsu.voltage) < fpsu.voltage * MAX_VARIANCE_FACTOR
    True
    >>> abs(fpsu.voltage_sense - fpsu.voltage) > fpsu.voltage * MAX_VARIANCE_FACTOR
    False
    >>> fpsu.voltage = 4.387
    >>> fpsu.voltage
    array(4.387) * V

    >>> fpsu.current
    array(15.5) * A
    >>> (fpsu.current_sense < fpsu._current)
    True
    >>> fpsu.current = 10.2
    >>> fpsu.current
    array(10.2) * A

    >>> fpsu.output = True
    >>> fpsu.output
    True
    >>> fpsu.output = False
    >>> fpsu.output
    False
    """
    def __init__(self):
        self._output = False
        self._voltage = 5.0 * pq.V
        self._current = 15.5 * pq.A

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, quantity):
        if isinstance(quantity, (int, float)):
            self._voltage = quantity * pq.V
        else:
            self._voltage = quantity.rescale(pq.V)

    @property
    def voltage_sense(self):
        if self._output:
            max_variance = self._voltage * MAX_VARIANCE_FACTOR
            this_variance = ((random.random() * max_variance * 2)
                             - max_variance)
            return self._voltage + this_variance
        else:
            return random.random() * 0.01

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, quantity):
        if isinstance(quantity, (int, float)):
            self._current = quantity * pq.A
        else:
            self._current = quantity.rescale(pq.A)

    @property
    def current_sense(self):
        if self._output:
            return random.random() * self._current
        else:
            return random.random() * 0.01

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, boolean_value):
        if not isinstance(boolean_value, bool):
            raise Exception("Output state setting should be a bool.")
        self._output = boolean_value

    def reset(self):
        self.voltage = 0
        self.current = 0
        self.output = False


def main():
    cam = PiCamera()
    psu = HP6652a()

    cam.close()
    del psu

if __name__ == '__main__':
    main()
