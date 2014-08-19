import pickle
from django.db import models
import fields

class Experiment(models.Model):
    experiment_name = models.CharField(
        'descriptive name of experiment (optional)',
        max_length=250,
        null=True,
        blank=True,
    )
    experiment_start_dtg = models.DateTimeField(
        'start date/time of experiment'
    )
    experiment_last_viewed = models.DateTimeField(
        'last time the experiment was opened'
    )


class Image(models.Model):
    """
    Each captured image will be stored as the path of the file that
    contains the actual image and the metadata available at
    capture time.
    """

    # Link to a specific experiment
    experiment = models.ForeignKey(Experiment)

    # Data available at capture time.
    dtg_capture = models.DateTimeField('DTG of image capture')
    species = models.CharField('species of fish', max_length=50)
    voltage = models.FloatField('voltage at power supply', default=0)

    # TODO: change to FilePathField when ready to start testing with actual images
    filename = models.TextField(
        'path of image file',
    )


class ImageAnalysis(models.Model):
    # link to a specific image
    image = models.ForeignKey(Image)

    # Data available after processing.
    analysis_dtg = models.DateTimeField(
        'the time/date that this analysis was performed'
    )
    orientation = models.SmallIntegerField(
        'angle between the water flow source and the fish',
        default=None,
    )
    location = fields.LocationField(
        'the x,y coordinates of the fish in the image',
    )
    silhouette = fields.ContourField(
        'The OpenCV contour of the outline of the fish'
    )

    # Verification
    _VERIFICATION_KWARGS = dict()
    _VERIFICATION_KWARGS['blank'] = True
    _VERIFICATION_KWARGS['null'] = True

    verified_dtg = models.DateTimeField(
        'the dtg at which verification took place',
        **_VERIFICATION_KWARGS
    )
    verified_by = models.CharField(
        max_length=100,
        **_VERIFICATION_KWARGS
    )


class HopperChain(models.Model):
    hopperchain_name = models.CharField(
        'descriptive name of hopperchain (optional)',
        max_length=250,
        blank=True,
    )
    hopperchain_spec = fields.HopperchainSpecField(
        'specification of hopperchain',
    )


