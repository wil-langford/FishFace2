"""
"""

import random

import instruments.units as units
import quantities as pq

MAX_VARIANCE_FACTOR = 0.05


class FakePowersupply(object):
    """
    >>> fpsu = FakePowersupply()
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

    >>> fpsu.output
    """
    def __init__(self):
        self._voltage = 5.0 * pq.V
        self._current = 15.5 * pq.A

    @property
    def voltage(self):
        return self._voltage
    @voltage.setter
    def voltage(self, quantity):
        if isinstance(quantity, (int,float)):
            self._voltage = quantity * pq.V
        else:
            self._voltage = quantity.rescale(pq.V)

    @property
    def voltage_sense(self):
        max_variance = self._voltage * MAX_VARIANCE_FACTOR
        this_variance = ((random.random() * max_variance * 2)
                         - max_variance)
        return self._voltage + this_variance


    @property
    def current(self):
        return self._current
    @current.setter
    def current(self, quantity):
        if isinstance(quantity, (int,float)):
            self._current = quantity * pq.A
        else:
            self._current = quantity.rescale(pq.A)

    @property
    def current_sense(self):
        return random.random() * self._current

    @property
    def output(self):
        raise Exception("Cannot read output state of PSU; can only set it.")
    @output.setter
    def output(self, boolean_value):
        if not isinstance(boolean_value, bool):
            raise Exception("Output state setting should be a bool.")

