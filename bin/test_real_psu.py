import unittest
import time
import random

import etc.fishface_config as ff_conf

VOLTAGE_ALLOWABLE_ERROR = 0.005
CURRENT_ALLOWABLE_ERROR = 0.005

MAX_CURRENT = 10

MIN_V = 4
MAX_V = 8
V_RANGE = MAX_V - MIN_V


def delay_until(unix_timestamp):
    now = time.time()
    while now < unix_timestamp:
        time.sleep(unix_timestamp-now)
        now = time.time()


def delay_for_seconds(seconds):
    later = time.time() + seconds
    delay_until(later)


class CommCheckTest(unittest.TestCase):

    def setUp(self):
        self.psu = ff_conf.PSU_CLASS()
        self.psu.voltage = 0
        self.psu.current = MAX_CURRENT
        self.output = True

    def test_communication_with_power_supply(self):
        self.assertIsInstance(self.psu.name, basestring)

    def test_correct_instrument(self):
        self.assertEqual(self.psu.name, "HEWLETT-PACKARD 6652A")

    def test_set_psu_to_ten_random_voltages(self):

        voltage_set = round(MIN_V + random.random() * V_RANGE, 3)
        self.psu.voltage = voltage_set

    def test_sensed_voltage_close_to_five_random_set_voltages(self):
        set_voltages = [round(MIN_V + random.random() * V_RANGE, 3) for i in range(5)]
        for voltage_set in set_voltages:
            self.psu.voltage = voltage_set

            voltage_set_read_back = float(self.psu.voltage)
            self.assertEqual(voltage_set, voltage_set_read_back)

            voltage_sensed = float(self.psu.voltage_sense)
            self.assertAlmostEqual(voltage_set, voltage_sensed, delta=voltage_set * VOLTAGE_ALLOWABLE_ERROR)

            current_sensed = float(self.psu.current)
            self.assertLessEqual(current_sensed, MAX_CURRENT  * (1 + CURRENT_ALLOWABLE_ERROR))

            delay_for_seconds(0.5)

    def tearDown(self):
        self.psu.current = 0
        self.psu.voltage = 0
        self.output = False
        del self.psu

if __name__ == '__main__':
    unittest.main()