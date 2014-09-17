from django.db import models
import django.utils as du
import fields
import django.dispatch.dispatcher
import django.db.models.signals as ddms
import django.core.urlresolvers as dcu
from django.conf import settings

class Species(models.Model):
    name = models.CharField('the full species of the fish', max_length=200,
                            default='genus species', unique=True)
    common_name = models.CharField('the common name of the fish species', max_length=200,
                                   blank=True, null=True, unique=True)
    shortname = models.CharField('a short abbreviation for the species of fish', max_length=5,
                                 default='ABC', unique=True)
    image = models.ImageField('a sample image of the fish species',
                              blank=True, null=True, upload_to="species_sample_images" )

    def inline_image(self):
        return '<img width=200 src="/media/{}" />'.format(
            self.image
        )
    inline_image.allow_tags = True

    def linked_inline_image(self):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.image,
            self.inline_image(),
        )
    linked_inline_image.allow_tags = True

    def __unicode__(self):
        return u'{}({})'.format(
            self.name,
            self.shortname,
        )

    def get_absolute_url(self):
        return dcu.reverse(
            'djff:sp_update',
            kwargs={'pk': self.pk}
        )


class Experiment(models.Model):
    """
    The model for xp-level data.
    """
    name = models.CharField('descriptive name of xp', max_length=250, default='New Experiment' )
    xp_start = models.DateTimeField('start date/time of xp')
    species = models.ForeignKey(Species)
    researcher = models.ForeignKey(Researcher, null=True, blank=True)

    def __unicode__(self):
        return "{} (XP-{})".format(
            self.name,
            self.id,
        )


class CaptureJobRecord(models.Model):
    xp = models.ForeignKey(Experiment)
    voltage = models.FloatField(default=0)
    current = models.FloatField(default=18)

    job_start = models.DateTimeField(null=True, blank=True)
    running = models.NullBooleanField(default=None)
    total = models.IntegerField(null=True, blank=True)
    remaining = models.IntegerField(null=True, blank=True)
    job_stop = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u'CaptureJobRecord {} (XP-{}_CJR_{})'.format(self.id,
                                                     self.xp.id,
                                                     self.id)


class Image(models.Model):
    """
    Each captured image will be stored as the path of the file that
    contains the actual image and the metadata available at
    capture time.
    """

    xp = models.ForeignKey(Experiment, editable=False, )
    cjr = models.ForeignKey(CaptureJobRecord, null=True, editable=False, )

    # Data available at capture time.
    capture_timestamp = models.DateTimeField('DTG of image capture', default=du.timezone.now() )
    voltage = models.FloatField('voltage at power supply', default=0 )
    image_file = models.ImageField('path of image file',
                                   upload_to="experiment_imagery/stills/%Y.%m.%d")
    is_cal_image = models.BooleanField('is this image a calibration image?', default=False )

    def inline_image(self):
        return '<img width=200 src="{}{}" />'.format(
            settings.MEDIA_URL, self.image_file
        )
    inline_image.allow_tags = True

    def linked_inline_image(self):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.image_file,
            self.inline_image(),
        )
    linked_inline_image.allow_tags = True

    def linked_inline_bullet(self):
        return '<a href="/media/{}" target="_newtab">X</a>'.format(
            self.image_file,
        )
    linked_inline_image.allow_tags = True


class ImageAnalysis(models.Model):
    # link to a specific image
    image = models.ForeignKey(Image)

    # Data available after processing.
    analysis_datetime = models.DateTimeField('the time/date that this analysis was performed')
    orientation = models.SmallIntegerField('angle between the water flow source and the fish',
                                           default=None)
    location = fields.LocationField('the x,y coordinates of the fish in the image')
    silhouette = fields.ContourField('The OpenCV contour of the outline of the fish')

    verified_dtg = models.DateTimeField('the dtg at which verification took place',
                                        blank=True, null=True)
    verified_by = models.ForeignKey(Researcher)


class ManualMeasurement(models.Model):
    orientation = models.SmallIntegerField('angle between the water flow source and the fish',
                                           default=None)
    analysis_datetime = models.DateTimeField('the time/date that this analysis was performed')
    researcher = models.ForeignKey(Researcher)


class CaptureJobTemplate(models.Model):
    voltage = models.FloatField('the voltage that the power supply will be set to', default=0, )
    current = models.FloatField('maximum current in amps that the power supply will provide', default=15, )
    duration = models.FloatField('the number of seconds to run the job', default=0, )
    interval = models.FloatField('the number of seconds between image captures', default=1, )
    startup_delay = models.FloatField(
        'the number of seconds to delay between setting voltage and image capture',
        default=30.0
    )

    def get_absolute_url(self):
        return dcu.reverse(
            'djff:cjt_update',
            kwargs={'pk': self.pk}
        )


class Fish(models.Model):
    species = models.ForeignKey(Species)
    comment = models.TextField('description of the fish (optional)')


class FishLocale(models.Model):
    fish = models.ForeignKey(Fish)
    tank = models.CharField('the tank holding the fish', max_length=50)
    datetime_in_tank = models.DateTimeField('the date and time that the fish was in the tank')


class Researcher(models.Model):
    name = models.CharField('name of the researcher', max_length=200)
    email = models.EmailField('email address of the researcher (optional)', null=True, blank=True)


@django.dispatch.dispatcher.receiver(ddms.post_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # pass False so ImageField won't save the model
    instance.image_file.delete(False)