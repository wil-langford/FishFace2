import time
import threading
import subprocess
import logging

import RPi.GPIO as gpio


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filename='/home/pi/raspi_privileged_server.log',)

logger = logging.getLogger(__name__)

__author__ = 'wil-langford'


class Pin(object):
    def __init__(self, pin):
        gpio.setmode(gpio.BCM)
        self.pin = pin

    def cleanup(self):
        gpio.cleanup(self.pin)
        logger.info("Pin on BCM pin {} has been cleaned up.".format(
            self.pin
        ))


class PinLight(Pin):
    def __init__(self, pin):
        super(PinLight, self).__init__(pin)
        logger.info("PinLight created on BCM pin {}".format(pin))
        gpio.setup(pin, gpio.OUT)

    def light(self, light_up):
        if light_up:
            new_state = 'on'
        else:
            new_state = 'off'

        logger.info("Turning {} PinLight on BCM pin {}".format(
            new_state,
            self.pin
        ))

        gpio.output(self.pin, bool(light_up))


class PinButton(Pin):
    def __init__(self, pin, callback,
                 pull_up_down=gpio.PUD_UP,
                 minimum_seconds_until_refire=0.5,
                 ):
        super(PinButton, self).__init__(pin)
        logger.info("PinButton created on BCM pin {}".format(pin))
        self.callback = callback
        self._keep_looping = True
        self._limit_refire = minimum_seconds_until_refire
        gpio.setup(pin, gpio.IN, pull_up_down=pull_up_down)

        logger.info("Defining loop function for thread.")

        def wait_for_falling_edge_loop():
            while True and self._keep_looping:
                logger.info("Waiting for falling edge " +
                "on BCM pin {}".format(self.pin)
                )
                gpio.wait_for_edge(self.pin, gpio.FALLING)
                logger.info("Falling edge detected on {}.".format(
                    self.pin))
                if self._keep_looping:
                    logger.info("Executing callback function.")
                    self.callback()
                time.sleep(self._limit_refire)

        logger.info("Starting new thread to wait for button press" +
        "on BCM pin {}.".format(self.pin))

        thread = threading.Thread(
            target=wait_for_falling_edge_loop,
        )
        thread.start()


def poweroff():
    logger.info("Powering off Raspberry Pi.")
    subprocess.call(['/sbin/poweroff'])


def main():
    light = PinLight(23)
    light.light(True)
    time.sleep(0.3)
    light.light(False)
    time.sleep(0.3)
    light.light(True)

    button = PinButton(25, poweroff)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        button.cleanup()
        gpio.cleanup()

if __name__ == '__main__':
    main()