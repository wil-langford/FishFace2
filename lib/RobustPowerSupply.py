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
import threading

import instruments as ik
from serial.serialutil import SerialException

logger = logging.getLogger('djff.raspi.power_supply')
logger.setLevel(logging.WARNING)

if not logger.handlers:

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    LOG_TO_CONSOLE = True
    CONSOLE_LOG_LEVEL = logging.DEBUG
    FILE_LOG_LEVEL = logging.DEBUG

    console_handler = logging.StreamHandler()
    console_handler.setLevel(CONSOLE_LOG_LEVEL)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('robust_power_supply.log')
    file_handler.setLevel(FILE_LOG_LEVEL)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    if LOG_TO_CONSOLE:
        logger.addHandler(console_handler)

# Instrument class
POWER_SUPPLY_CLASS = ik.hp.HP6652a

# Allowable variation between volts commanded and volts that the setting that the instrument reports.
VOLTAGE_TOLERANCE = 0.01
CURRENT_TOLERANCE = 0.01

MAX_ATTEMPTS = 10


class RobustPowerSupply(object):
    def __init__(self, port_device='/dev/ttyUSB0', gpib_address=2):
        self.psu = POWER_SUPPLY_CLASS.open_gpibusb(port_device,
                                                   gpib_address)
        self.psu_lock = threading.RLock()

        self._last_commanded_output_state = None

    @property
    def name(self):
        return self.psu.name

    @property
    def output(self):
        # If we haven't commanded the power supply's output state yet this session, try to figure out if its
        # output is enabled based on the sensed voltage and current, otherwise, return the last commanded
        # state.
        if self._last_commanded_output_state is None:
            logger.debug("Determining output state based on sensed current/voltage.")
            return bool(self.current_sense > 0.1 or self.voltage_sense > 0.1)
        else:
            return self._last_commanded_output_state

    @output.setter
    def output(self, enable_output):
        self._last_commanded_output_state = bool(enable_output)
        with self.psu_lock:
            self.psu.output = self._last_commanded_output_state

    @property
    def voltage(self):
        logger.info("Getting voltage setting from PSU.")
        read_voltage = None
        with self.psu_lock:
            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to read voltage setting from PSU.".format(attempt))

                try:
                    read_voltage = self.psu.voltage
                    break
                except (SerialException, ValueError):
                    pass

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to read voltage setting reached.")

        return read_voltage

    @voltage.setter
    def voltage(self, value):
        with self.psu_lock:
            if value == 0:
                self.output = False
                return

            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to set voltage.".format(attempt))

                try:
                    self.psu.voltage = value
                except (SerialException, ValueError):
                    pass

                if abs(float(self.voltage) - value) < VOLTAGE_TOLERANCE:
                    break

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to set voltage reached.")

    @property
    def voltage_sense(self):
        sensed_voltage = None
        with self.psu_lock:
            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to sense voltage from PSU.".format(attempt))

                try:
                    sensed_voltage = self.psu.voltage_sense
                    break
                except (SerialException, ValueError):
                    pass

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to sense voltage reached.")

        return sensed_voltage

    @property
    def current(self):
        logger.info("Getting current setting from PSU.")
        read_current = None
        with self.psu_lock:
            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to read current setting from PSU.".format(attempt))

                try:
                    read_current = self.psu.current
                    break
                except (SerialException, ValueError):
                    pass

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to read current setting reached.")

        return read_current

    @current.setter
    def current(self, value):
        with self.psu_lock:
            if value == 0:
                self.output = False
                return

            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to set current.".format(attempt))

                try:
                    self.psu.current = value
                except (SerialException, ValueError):
                    pass

                if abs(float(self.current) - value) < CURRENT_TOLERANCE:
                    break

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to set current reached.")

    @property
    def current_sense(self):
        sensed_current = None
        with self.psu_lock:
            for attempt in range(MAX_ATTEMPTS):
                logger.debug("Attempt {} to sense current from PSU.".format(attempt))

                try:
                    sensed_current = self.psu.current_sense
                    break
                except (SerialException, ValueError):
                    pass

                if attempt == MAX_ATTEMPTS:
                    logger.error("Maximum attempts to sense current reached.")

        return sensed_current

