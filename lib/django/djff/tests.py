from django.test import TestCase
from lib.django.djff.models import (Experiment, Species)
import lib.django.djff.views as views
import django.utils as du
from django.utils import timezone
from django.core.management import call_command
import django.utils.timezone as dut


class SpeciesTests(TestCase):
    def test_Initial_species_created_with_new_experiment(self):
        xp = views.experiment_new_init()
        self.assertTrue(xp.species)


