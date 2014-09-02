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


class ExperimentTests(TestCase):
    def test_Experiment_index_sorted_by_date(self):
############ Creating dummy data for testing ######################

        xp_list = []
        test_list = []
        for count in range(0,3):
            xp_list.append(djff.views.experiment_new_init())

###################################################################

        experiment_list = djff.views.experiment_index_init()

        for experiment in experiment_list:
            test_list.append(experiment.experiment_start_dtg)

        self.assertTrue(test_list == sorted(test_list))