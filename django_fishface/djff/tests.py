from django.test import TestCase
from djff.models import Experiment
from djff.models import Species
import djff.views
import django.utils as du
from django.utils import timezone
from django.core.management import call_command
import django.utils.timezone as dut

# Create your tests here.
class SpeciesTests(TestCase):
    def test_Experiment_references_species(self):
  	    # simpleExperiment = djff.views.experiment_new('testing')
  	    sampleSpecies = Species(species_name='plucko', species_shortname='p')
  	    sampleSpecies.save()
  	    sampleExperiment = Experiment(experiment_name='nick_trial', experiment_start_dtg=timezone.now(), species=Species.objects.all()[0])
  	    sampleExperiment.save()
  	    self.assertEqual(sampleExperiment.species.species_name, 'plucko')

    def test_initial_species_created_with_new_experiment(self):
        xp = Experiment()
        xp.experiment_start_dtg = du.timezone.now()
        xp.experiment_name = "New experiment"
        try:
            xp.species = Species.objects.all()[0]
        except IndexError:
            defaultSpecies = Species()
            defaultSpecies.species_name = "hypostomus plecostomus"
            defaultSpecies.species_shortname = "HP"
            defaultSpecies.save()
            xp.species = defaultSpecies

        xp.save()
        self.assertEqual(xp.species.species_name, defaultSpecies.species_name)


