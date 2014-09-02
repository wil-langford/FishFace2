from django.test import TestCase
from djff.models import Experiment
from djff.models import Species
import djff.views
import django.utils as du
from django.utils import timezone
from django.core.management import call_command
import django.utils.timezone as dut


class SpeciesTests(TestCase):
    def test_Initial_species_created_with_new_experiment(self):
        xp = djff.views.experiment_new_init()
        self.assertTrue(xp.species)


