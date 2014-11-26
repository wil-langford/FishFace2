"""
I hate this module, but it's necessary.  The power supply we're using is overkill for what we're doing in terms of
accuracy and ability to deliver electrons, BUT the control interface is flaky and I'm tired of trying to troubleshoot
that instead of working on FishFace.  Hence, this subclass of the power supply class will do things like set the power
and then *check* it to make sure it got set.

On the measurement side, it will keep trying to get a measurement until it obtains one or reaches a threshold of
iterations.

The only *real* functional improvement is that the output status (enabled or disabled) of the power supply is readable
here, whereas it's write-only on the actual instrument.
"""
import logging

import instruments as ik
from serial.serialutil import SerialException
import quantities as pq

logger = logging.getLogger('raspi')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

LOG_TO_CONSOLE = True
CONSOLE_LOG_LEVEL = logging.DEBUG
FILE_LOG_LEVEL = logging.DEBUG

console_handler = logging.StreamHandler()
console_handler.setLevel(CONSOLE_LOG_LEVEL)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('imagery_server.log')
file_handler.setLevel(FILE_LOG_LEVEL)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
if LOG_TO_CONSOLE:
    logger.addHandler(console_handler)

# Instrument parent class
POWER_SUPPLY_PARENT_CLASS = ik.hp.HP6652a

# Allowable variation between volts commanded and volts that the setting that the instrument reports.
VOLTAGE_TOLERANCE = 0.01
CURRENT_TOLERANCE = 0.01

MAX_ATTEMPTS = 10

# This next line is where you specify which InstrumentKit power supply we are wrapping.
class RobustPowerSupply(POWER_SUPPLY_PARENT_CLASS):
    def __init__(self, *args, **kwargs):
        super(RobustPowerSupply, self).__init__(*args, **kwargs)

        self._last_commanded_output_state = None
        self._output = super(RobustPowerSupply, self).output

        self._voltage = super(RobustPowerSupply, self).voltage
        self._current = super(RobustPowerSupply, self).current

    @property
    def output(self):
        return self._last_commanded_output_state

    @output.setter
    def output(self, enable_output):
        self._last_commanded_output_state = bool(enable_output)
        self._output = self._last_commanded_output_state

    @property
    def voltage(self):
        attempts = 0
        read_voltage = None
        while attempts < MAX_ATTEMPTS and read_voltage is None:
            attempts += 1
            try:
                read_voltage = self._voltage
            except SerialException, ValueError:
                pass
        else:
            if attempts == MAX_ATTEMPTS:
                logger.error("Maximum attempts to get voltage reached.")

        return read_voltage

    @voltage.setter
    def voltage(self, value):
        attempts = 0
        while abs(float(self._voltage) - value) < VOLTAGE_TOLERANCE and attempts < MAX_ATTEMPTS:
            attempts += 1
            self._voltage = value
        else:
            if attempts == MAX_ATTEMPTS:
                logger.error("Maximum attempts to set voltage reached.")

    @property
    def current(self):
        attempts = 0
        read_current = None
        while attempts < MAX_ATTEMPTS and read_current is None:
            attempts += 1
            try:
                read_current = self._current
            except SerialException, ValueError:
                pass
        else:
            if attempts == MAX_ATTEMPTS:
                logger.error("Maximum attempts to get current reached.")

        return read_current

    @current.setter
    def current(self, value):
        print "DEBUG {}".format(value)
        attempts = 0
        while float(self._current) < value + CURRENT_TOLERANCE and attempts < MAX_ATTEMPTS:
            attempts += 1
            self._current = value
        else:
            if attempts == MAX_ATTEMPTS:
                logger.error("Maximum attempts to set current reached.")