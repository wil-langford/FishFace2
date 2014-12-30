import math

from django.db import models
import django.dispatch.dispatcher
import django.db.models.signals as ddms
import django.core.urlresolvers as dcu
from django.conf import settings

import fields
from utils import djff_imagekit as ffik


class Species(models.Model):
    name = models.CharField('the full species of the fish', max_length=200,
                            default='genus species', unique=True)
    common_name = models.CharField('the common name of the fish species', max_length=200,
                                   blank=True, null=True, unique=True)
    shortname = models.CharField('a short abbreviation for the species of fish', max_length=5,
                                 default='ABC', unique=True)
    image = models.ImageField('a sample image of the fish species',
                              blank=True, null=True, upload_to="species_sample_images")

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


class Researcher(models.Model):
    name = models.CharField('name of the researcher', max_length=200)
    email = models.EmailField('email address of the researcher (optional)', null=True, blank=True, )

    def __unicode__(self):
        return u'{}'.format(self.name)

    @property
    def tag_score(self):
        return self.manualtag_set.count()


class PowerSupplyLog(models.Model):
    measurement_datetime = models.DateTimeField('timestamp of measurement', auto_now_add=True)
    current_meas = models.FloatField('current measured by power supply', null=True)
    voltage_meas = models.FloatField('voltage measured by power supply', null=True)


class Experiment(models.Model):
    """
    The model for xp-level data.
    """
    name = models.CharField('descriptive name of xp', max_length=250, default='New Experiment')
    xp_start = models.DateTimeField('start date/time of xp')
    species = models.ForeignKey(Species)
    comment = models.TextField('general comments about this experiment (optional)',
                               null=True, blank=True, )
    researcher = models.ForeignKey(Researcher, null=True, blank=True)

    def __unicode__(self):
        return "{} ({})".format(
            self.name,
            self.slug,
        )

    @property
    def slug(self):
        return u"XP_{}".format(self.id)


class CaptureJobRecord(models.Model):
    xp = models.ForeignKey(Experiment)
    voltage = models.FloatField(default=0)
    current = models.FloatField(default=18)

    researcher = models.ForeignKey(Researcher, null=True, blank=True)

    job_start = models.DateTimeField(null=True, blank=True)
    running = models.NullBooleanField(default=None)
    total = models.IntegerField(null=True, blank=True)
    remaining = models.IntegerField(null=True, blank=True)
    job_stop = models.DateTimeField(null=True, blank=True)

    comment = models.TextField('general comments about this Capture Job Record (optional)',
                               null=True, blank=True, )

    def __unicode__(self):
        return u'CaptureJobRecord {} (XP-{}_CJR_{})'.format(self.id,
                                                            self.xp.id,
                                                            self.id)

    @property
    def slug(self):
        return u'CJR_{}'.format(self.id)

    @property
    def full_slug(self):
        return self.xp.slug + "_" + self.slug

    @property
    def image_count(self):
        return Image.objects.filter(cjr__pk=self.pk).count()


class Image(models.Model):
    """
    Each captured image will be stored as the path of the file that
    contains the actual image and the metadata available at
    capture time.
    """

    xp = models.ForeignKey(Experiment, editable=False, )
    cjr = models.ForeignKey(CaptureJobRecord, null=True, editable=False, )

    # Data available at capture time.
    capture_timestamp = models.DateTimeField('DTG of image capture', auto_now_add=True)
    voltage = models.FloatField('voltage at power supply', default=0)
    image_file = models.ImageField('path of image file',
                                   upload_to="experiment_imagery/stills/%Y.%m.%d")
    is_cal_image = models.BooleanField('is this image a calibration image?', default=False)

    psu_log = models.ForeignKey(PowerSupplyLog,
                                null=True, blank=True)

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


class ManualTag(models.Model):
    image = models.ForeignKey(Image)
    timestamp = models.DateTimeField('DTG of image capture', auto_now_add=True)
    start = models.CommaSeparatedIntegerField('the point in the image where the tag arrow starts',
                                              max_length=20)
    end = models.CommaSeparatedIntegerField('the point in the image where the tag arrow ends',
                                            max_length=20)
    researcher = models.ForeignKey(Researcher)

    @property
    def int_start(self):
        return tuple(int(x) for x in self.start.split(','))

    @property
    def int_end(self):
        return tuple(int(x) for x in self.end.split(','))

    @property
    def vector(self):
        return tuple(e - s for s, e in zip(self.int_start, self.int_end))

    @property
    def angle(self):
        start = self.int_start
        end = self.int_end

        return math.atan2(
            end[1] - start[1],
            end[0] - start[0]
        )

    @property
    def degrees(self):
        return math.degrees(self.angle)

    def verification_image(self):
        generator = ffik.ManualTagVerificationThumbnail(
            tag=self,
            source=self.image.image_file
        )
        image = generator.generate()
        return image


class ManualVerification(models.Model):
    tag = models.ForeignKey(ManualTag)
    timestamp = models.DateTimeField('DTG of image capture', auto_now_add=True)
    researcher = models.ForeignKey(Researcher)


class CaptureJobTemplate(models.Model):
    voltage = models.FloatField('the voltage that the power supply will be set to', default=0, )
    current = models.FloatField('maximum current in amps that the power supply will provide',
                                default=15)
    duration = models.FloatField('the number of seconds to run the job', default=0, )
    interval = models.FloatField('the number of seconds between image captures', default=1, )
    startup_delay = models.FloatField(
        'the number of seconds to delay between setting voltage and image capture',
        default=30.0
    )
    description = models.TextField('a description of this capture job template (optional)',
                                   null=True, blank=True, )

    def get_absolute_url(self):
        return dcu.reverse(
            'djff:cjt_update',
            kwargs={'pk': self.pk}
        )


class Fish(models.Model):
    species = models.ForeignKey(Species)
    comment = models.TextField('description of the fish (optional)',
                               blank=True, null=True)

    def last_seen_in(self):
        fl = FishLocale.objects.filter(fish=self.id).order_by('datetime_in_tank')[0]
        return fl.tank.short_name

    @property
    def slug(self):
        return u'{}_{}'.format(self.species.shortname, self.id)


class Tank(models.Model):
    short_name = models.CharField('a short tag describing the tank',
                                  max_length=10, default='', unique=True)
    description = models.TextField('a longer name or description of the tank (optional)',
                                   null=True, blank=True, )

    def __unicode__(self):
        return u'{}'.format(self.short_name)


class FishLocale(models.Model):
    fish = models.ForeignKey(Fish)
    tank = models.ForeignKey(Tank)
    datetime_in_tank = models.DateTimeField('the date and time that the fish was in the tank',
                                            auto_now_add=True)


@django.dispatch.dispatcher.receiver(ddms.post_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # pass False so ImageField won't save the model
    instance.image_file.delete(False)