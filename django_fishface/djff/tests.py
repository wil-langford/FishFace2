from django.test import TestCase
from djff.models import Experiment
from djff.models import Species
import djff.views
from django.utils import timezone
from django.core.management import call_command

# Create your tests here.
class SpeciesTests(TestCase):
  def test_Experiment_references_species(self):
  	# simpleExperiment = djff.views.experiment_new('testing')
  	sampleSpecies = Species(species_name='plucko', species_shortname='p')
  	sampleSpecies.save()
  	sampleExperiment = Experiment(experiment_name='nick_trial', experiment_start_dtg=timezone.now(), species=Species.objects.all()[0])
  	sampleExperiment.save()
  	self.assertEqual(sampleExperiment.species.species_name, 'plucko')