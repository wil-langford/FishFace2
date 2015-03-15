import os
import time

import celery

from fishface_celery import celery_app
from util.fishface_logging import logger

import util.fishface_config as ff_conf


@celery.shared_task(bind=True, name='psu.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


class PowerSupply(object):
    def __init__(self):
        self.voltage = None
        self.current = None
        self.output = None
        self.psu = None

    def open(self):
        if self.psu is not None:
            return False

        self.psu = ff_conf.PSU_CLASS()
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
                'current_meas': self.psu.current_sense,
                'voltage_meas': self.psu.voltage_sense,
            }

        if extra_report_data is not None:
            state['extra_report_data'] = extra_report_data

        celery_app.send_task('django.power_supply_report', kwargs=state)

        return True


power_supply = PowerSupply()
power_supply.open()

@celery.shared_task(name="psu.set_psu")
def set_psu(*args, **kwargs):
    global power_supply
    power_supply.set_psu(*args, **kwargs)


@celery.shared_task(name='psu.reset_psu')
def reset_psu():
    global power_supply
    power_supply.set_psu(reset=True)


@celery.shared_task(name="psu.report")
def report(extra_report_data=None):
    global power_supply
    power_supply.report(extra_report_data)


class PowerSupplyError(Exception):
    pass