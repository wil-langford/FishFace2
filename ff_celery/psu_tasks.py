import os
import time

import celery

from fishface_celery import celery_app
from util.fishface_logging import logger


REAL_HARDWARE = not os.path.isfile('FAKE_THE_HARDWARE')


class PowerSupply(object):
    def __init__(self, real=True):
        self.real = bool(real)

        self.voltage = None
        self.current = None
        self.output = None
        self.psu = None

        if self.real:
            logger.info('Running with real power supply.')
            from util import RobustPowerSupply

            self.psu_class = RobustPowerSupply.RobustPowerSupply
        else:
            logger.warning('Running with fake power supply.')
            from util import FakeHardware

            self.psu_class = FakeHardware.HP6652a

    def open(self):
        if self.psu is not None:
            return False

        self.psu = self.psu_class()
        self.voltage = self.psu.voltage
        self.current = self.psu.current
        self.output = self.psu.output

        return True

    def close(self):
        if self.psu is None:
            return False

        self.voltage = None
        self.current = None
        self.output = None
        self.psu = None

        return True

    def reset(self):
        self.set_psu(reset=True)

    def set_psu(self, voltage=False, current=False, output=False, reset=False):
        if self.psu is None:
            return False

        if reset:
            voltage = 0
            current = 0
            output = False
            self.psu.reset()

        if voltage:
            logger.info("setting psu voltage to {} V".format(
                voltage
            ))
            self.psu.voltage = voltage
        else:
            self.psu.voltage = 0

        if current:
            logger.info("setting psu max current to {} A".format(
                current
            ))
            self.psu.current = current
        else:
            self.psu.current = 0

        if output:
            logger.info("enabling psu output")
        else:
            logger.info("disabling psu output")

        self.psu.output = output

        self.report()

        return True

    def report(self, extra_report_data=None):
        if self.psu is None:
            return False
        else:
            state = {
                'timestamp': time.time(),
                'current': self.psu.current,
                'voltage': self.psu.voltage,
                'output': self.psu.output,
            }

        if extra_report_data is not None:
            state['extra_report_data'] = extra_report_data

        celery_app.send_task('django.power_supply_report', kwargs=state)

        return True


power_supply = PowerSupply(real=REAL_HARDWARE)
power_supply.open()


@celery.shared_task(name="psu.set_psu")
def set_psu(*args, **kwargs):
    power_supply.set_psu(*args, **kwargs)


@celery.shared_task(name="psu.report")
def report(extra_report_data=None):
    power_supply.report(extra_report_data)


class PowerSupplyError(Exception):
    pass