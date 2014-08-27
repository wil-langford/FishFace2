from django.db import models
import django.utils as du
import fields
import django.dispatch.dispatcher
import django.db.models.signals as ddms


class Species(models.Model):
    species_name = models.CharField(
        'the full species of the fish',
        max_length=200,
        default='full name of fish species',
    )
    species_shortname = models.CharField(
        'a short abbreviation for the species of fish',
        max_length=200,
        default='ABC',
    )
    sample_image = models.ImageField(
        'a sample image of the fish species',
        blank=True,
        null=True,
        upload_to="species_sample_images"
    )

    def inline_image(self):
        return '<img width=200 src="/media/{}" />'.format(
            self.sample_image
        )
    inline_image.allow_tags = True

    def linked_inline_image(self):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.sample_image,
            self.inline_image(),
        )
    linked_inline_image.allow_tags = True


    def __unicode__(self):
        return u'{}({})'.format(
            self.species_name,
            self.species_shortname,
        )


class Experiment(models.Model):
    """
    The model for experiment-level data.
    """
    experiment_name = models.CharField(
        'descriptive name of experiment',
        max_length=250,
        default='New Experiment'
    )
    experiment_start_dtg = models.DateTimeField(
        'start date/time of experiment'
    )
    species = models.ForeignKey(Species)

    researcher_name = models.CharField(
        'the name of the researcher',
        max_length=100,
        null=True,
        blank=True
    )
    researcher_email = models.EmailField(
        'the email address of the researcher',
        null=True,
        blank=True
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
    dtg_capture = models.DateTimeField(
        'DTG of image capture',
        default=du.timezone.now()
    )
    voltage = models.FloatField(
        'voltage at power supply',
        default=0
    )

    image_file = models.ImageField(
        'path of image file',
        upload_to="experiment_imagery/stills/%Y.%m.%d"
    )

    is_cal_image = models.BooleanField(
        'is this image a calibration image?',
        default=False
    )

    # TODO: check to see if there's a way to look up '/media/' instead
    # TODO: of hard coding it

    def inline_image(self):
        return '<img width=200 src="/media/{}" />'.format(
            self.image_file
        )
    inline_image.allow_tags = True

    def linked_inline_image(self):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.image_file,
            self.inline_image(),
        )
    linked_inline_image.allow_tags = True


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


@django.dispatch.dispatcher.receiver(ddms.post_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # pass False so ImageField won't save the model
    instance.image_file.delete(False)