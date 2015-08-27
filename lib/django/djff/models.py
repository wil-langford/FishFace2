import math
import datetime
import collections
import random

from django.db import models
import django.dispatch.dispatcher
import django.db.models as ddm
import django.db.models.signals as ddms
import django.core.urlresolvers as dcu
import django.utils.dateformat as dud
import django.utils.timezone as dut

from django.conf import settings
from lib.fishface_logging import logger

import numpy as np

import jsonfield

import sklearn.cluster as skc
import sklearn.preprocessing as skp

import lib.django.djff.utils.djff_imagekit as ffik


class Species(models.Model):
    name = models.CharField('the full species of the fish', max_length=200,
                            default='genus species', unique=True)
    common_name = models.CharField('the common name of the fish species', max_length=200,
                                   blank=True, null=True, unique=True)
    shortname = models.CharField('a short abbreviation for the species of fish', max_length=5,
                                 default='ABC', unique=True)
    image = models.ImageField('a sample image of the fish species',
                              blank=True, null=True, upload_to="species_sample_images")

    def inline_image(self, thumb=False):
        width = [200, 30][thumb]
        return '<img width={} class="inline_image" src="/media/{}" />'.format(
            width,
            self.image
        )
    inline_image.allow_tags = True

    def linked_inline_image(self, thumb=False):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.image,
            self.inline_image(thumb=thumb),
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
    bad_tags = models.IntegerField(
        "how many of this researcher's tags have been deleted during validation",
        default=0)

    def __unicode__(self):
        return u'{}'.format(self.name)

    @property
    def tag_score(self):
        return self.manualtag_set.count()

    @property
    def all_tags_count(self):
        return self.tag_score + self.bad_tags

    @property
    def unverified_tags(self):
        tags = self.manualtag_set.filter(researcher=self.id).annotate(ver_count=ddm.Count('manualverification'))
        return tags.filter(ver_count=0).count()

    @property
    def verified_tags(self):
        tags = self.manualtag_set.filter(researcher=self.id).annotate(ver_count=ddm.Count('manualverification'))
        return tags.filter(ver_count__gt=0).count()

    @property
    def accuracy_score(self):
        try:
            return round(float(self.verified_tags) / (self.all_tags_count - self.unverified_tags), 3)
        except ZeroDivisionError:
            return None

    @property
    def antiaccuracy_score(self):
        try:
            return round(float(self.bad_tags) / (self.all_tags_count - self.unverified_tags), 3)
        except ZeroDivisionError:
            return None


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

    @property
    def search_min(self):
        cjrs_with_mins = self.capturejobrecord_set.filter(search_min__isnull=False)
        if cjrs_with_mins.count()>0:
            return int(cjrs_with_mins.aggregate(ddm.Avg('major_min'))['search_min__avg'])
        else:
            return None

    @property
    def search_max(self):
        cjrs_with_maxes = self.capturejobrecord_set.filter(search_max__isnull=False)
        if cjrs_with_maxes.count()>0:
            return int(cjrs_with_maxes.aggregate(ddm.Avg('major_max'))['search_max__avg'])
        else:
            return None

    @property
    def color_min(self):
        cjrs_with_mins = self.capturejobrecord_set.filter(color_min__isnull=False)
        if cjrs_with_mins.count()>0:
            return int(cjrs_with_mins.aggregate(ddm.Avg('color_min'))['color_min__avg'])
        else:
            return None

    @property
    def color_max(self):
        cjrs_with_maxes = self.capturejobrecord_set.filter(color_max__isnull=False)
        if cjrs_with_maxes.count()>0:
            return int(cjrs_with_maxes.aggregate(ddm.Avg('color_max'))['color_max__avg'])
        else:
            return None


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

    major_min = models.IntegerField('the minimum length of the major axis of the ellipse' +
                                     'to search for during ellipse search tagging',
                                     null=True, blank=True)
    major_max = models.IntegerField('the maximum length of the major axis of the ellipse' +
                                     'to search for during ellipse search tagging',
                                     null=True, blank=True)

    color_min = models.IntegerField('the minimum color to search for during ellipse search tagging',
                                    null=True, blank=True)
    color_max = models.IntegerField('the maximum color to search for during ellipse search tagging',
                                    null=True, blank=True)

    ratio_min = models.FloatField('the minimum axes length ratio of the ellipse' +
                                     'to search for during ellipse search tagging',
                                     null=True, blank=True)
    ratio_max = models.FloatField('the minimum axes length ratio of the ellipse' +
                                     'to search for during ellipse search tagging',
                                     null=True, blank=True)

    comment = models.TextField('general comments about this Capture Job Record (optional)',
                               null=True, blank=True, )

    @property
    def search_envelope(self):
        envelope = dict()
        attribs = 'major color ratio'.split(' ')
        names = ([x + '_min' for x in attribs] + [x + '_max' for x in attribs])
        for name in names:
            envelope[name] = getattr(self, name, None)
            if envelope[name] is None:
                eligible_cjrs = self.xp.capturejobrecord_set.filter(major_min__isnull=False)
                if eligible_cjrs.count() > 0:
                    envelope[name] = eligible_cjrs.aggregate(ddm.Avg(name))[name + '__avg']

                    if name.split('_')[0] in 'search color'.split(' '):
                        envelope[name] = int(envelope[name])

            if envelope[name] is None:
                logger.warning("Couldn't get the search envelope for CJR ID: {}".format(self.id))
                return None

        return envelope

    def reset_search_envelope(self):
        attribs = 'major color ratio'.split(' ')
        names = ([x + '_min' for x in attribs] + [x + '_max' for x in attribs])
        for name in names:
            setattr(self, name, None)

        self.save()

    def __unicode__(self):
        return u'CaptureJobRecord {} (XP-{}_CJR_{})'.format(self.id,
                                                            self.xp.id,
                                                            self.id)

    @property
    def cal_image(self):
        cal_images = Image.objects.filter(
            xp_id=self.xp_id, is_cal_image=True
        ).order_by('capture_timestamp')
        return_image = None
        for ci in cal_images:
            if ci.capture_timestamp <= self.job_start:
                return_image = ci
            else:
                break

        return return_image

    @property
    def slug(self):
        return u'CJR_{}'.format(self.id)

    @property
    def full_slug(self):
        return self.xp.slug + "_" + self.slug

    @property
    def image_count(self):
        return Image.objects.filter(cjr__pk=self.pk).count()


def generate_image_filename(instance, filename):
    if instance.cjr_id is None and instance.is_cal_image:
        cjr_id = 0

    elif instance.cjr is None and not instance.is_cal_image:
        raise Exception("The CJR must be set on non-calibration images before setting the image " +
                        "so that the filename can be generated.")
    else:
        cjr_id = instance.cjr.id

    if not all([bool(x) for x in (instance, instance.xp_id, instance.capture_timestamp)]):
        raise Exception("The xp and capture_timestamp must be set before setting the image " +
                        "so that the filename can be generated.")
    utc_ts = round(float(dud.format(instance.capture_timestamp, 'U.u')), 2)
    temp_dt = datetime.datetime.utcfromtimestamp(utc_ts).replace(tzinfo=dut.utc)

    return (
        u'experiment_imagery/stills/{dtg}'.format(
            dtg=dud.format(instance.capture_timestamp, 'Y.m.d')
        ) +
        u'/XP-{instance.xp_id}_CJR-{cjr_id}_{instance.xp.species.shortname}_'.format(
            instance=instance,
            cjr_id=cjr_id
        ) +
        u'{file_dtg}_{file_ts}.jpg'.format(
            file_dtg=temp_dt.astimezone(dut.LocalTimezone()).strftime(
                settings.FILENAME_DATE_FORMAT),
            file_ts=utc_ts
        )
    )


class Image(models.Model):
    """
    Each captured image will be stored as the path of the file that
    contains the actual image and the metadata available at
    capture time.
    """

    xp = models.ForeignKey(Experiment, editable=False, )
    cjr = models.ForeignKey(CaptureJobRecord, null=True, editable=False, )

    # Data available at capture time.
    capture_timestamp = models.DateTimeField('DTG of image capture')
    voltage = models.FloatField('voltage at power supply', default=0)
    current = models.FloatField('current at power supply', default=0)
    image_file = models.ImageField('path of image file',
                                   upload_to=generate_image_filename)
    is_cal_image = models.BooleanField('is this image a calibration image?', default=False)

    bad_tags = models.IntegerField(
        "how many of this image's tags have been deleted during validation",
        default=0)

    @property
    def angle(self):
        my_tags = ManualTag.objects.filter(image=self)
        if my_tags.count() > 0:
            angle = sum(tag.angle for tag in my_tags) / float(my_tags.count())
        else:
            angle = None

        return angle

    @property
    def degrees(self):
        return None if self.angle is None else int(round(math.degrees(self.angle), 0))

    def inline_image(self, thumb=False):
        width = [200, 40][thumb]
        return '<img width={} class="inline_image" src="{}{}" />'.format(
            width, settings.MEDIA_URL, self.image_file
        )
    inline_image.allow_tags = True

    def linked_inline_image(self, thumb=False):
        return '<a href="/media/{}" target="_newtab">{}</a>'.format(
            self.image_file,
            self.inline_image(thumb),
        )
    linked_inline_image.allow_tags = True

    def linked_inline_bullet(self):
        return '<a href="/media/{}" target="_newtab">X</a>'.format(
            self.image_file,
        )
    linked_inline_bullet.allow_tags = True

    def linked_angle_bullet(self):
        return '<a href="/media/{}" class="angle_bullet" target="_newtab" data-angle="{}">X</a>'.format(
            self.image_file,
            self.degrees if self.degrees is not None else 'None',
        )
    linked_angle_bullet.allow_tags = True

    @property
    def latest_analysis(self):
        try:
            return ImageAnalysis.objects.filter(image_id=self.id).order_by("-analysis_datetime")[0]
        except IndexError:
            return None

    @property
    def latest_automatictag(self):
        try:
            return AutomaticTag.objects.filter(image_id=self.id).order_by("-timestamp")[0]
        except IndexError:
            return None

    @property
    def jpeg(self):
        with open(self.image_file.name, 'rb') as data_file:
            data = data_file.read()
        return data

    @property
    def cal_jpeg(self):
        with open(self.cjr.cal_image.image_file.name, 'rb') as cal_file:
            cal = cal_file.read()
        return cal

    @property
    def search_envelope(self):
        if not self.is_cal_image:
            return self.cjr.search_envelope
        else:
            logger.error("Cal images have no search envelopes.")
            return False

    @classmethod
    def untagged_image(cls, payload):
        untagged_images = cls.objects.filter(is_cal_image=False).exclude(
                xp__name__contains='TEST_DATA').exclude(
                manualtag__researcher__id__exact=int(payload['researcher_id']))

        if untagged_images.count() == 0:
            return {'valid': False,
                    'reason': 'zero_untagged'}
        else:
            max_id = untagged_images.aggregate(ddm.Max('id')).values()[0]
            min_id = math.ceil(max_id*random.random())
            untagged_image = untagged_images.filter(id__gte=min_id)[0]
            return {'id': untagged_image.id,
                    'valid': True}


class ImageAnalysis(models.Model):
    # link to a specific image
    image = models.ForeignKey(Image)

    # Data available after processing.
    analysis_datetime = models.DateTimeField('the time/date that this analysis was performed')
    silhouette = jsonfield.JSONField('The OpenCV contour of the outline of the fish')

    moments = jsonfield.JSONField('The image moments of the silhouette')
    hu_moments = jsonfield.JSONField('The Hu moments derived from the moments')

    meta_data = jsonfield.JSONField('Any metadata other than what gets its own field')

    @property
    def orientation_from_moments(self):
        # from http://en.wikipedia.org/wiki/Image_moment
        m00 = self.moments['m00']
        mu20p = self.moments['mu20'] / m00
        mu02p = self.moments['mu02'] / m00
        mu11p = self.moments['mu11'] / m00
        try:
            return math.degrees(0.5 * math.atan2(2 * mu11p, mu20p - mu02p))
        except ZeroDivisionError:
            return False

    @property
    def centroid(self):
        m00 = float(self.moments['m00'])
        m10 = float(self.moments['m10'])
        m01 = float(self.moments['m01'])

        x = int(m10 / m00)
        y = int(m01 / m00)

        return (x, y)


class AutomaticTag(models.Model):
    image = models.ForeignKey(Image)
    timestamp = models.DateTimeField('DTG of image capture', auto_now_add=True)
    image_analysis = models.ForeignKey(ImageAnalysis)

    centroid = jsonfield.JSONField('The center of mass of the fish')
    orientation = jsonfield.JSONField("Angle of the fish referenced against oncoming water flow")

    def __unicode__(self):
        return u'image_analysis_id({}) centroid({}) orientation({})'.format(
            self.image_analysis_id, self.centroid, self.orientation
        )


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

    @int_start.setter
    def int_start(self, value):
        self.start = ','.join(map(str, value))
        self.save()

    @int_end.setter
    def int_end(self, value):
        self.end = ','.join(map(str, value))
        self.save()

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

    @property
    def verification_image(self):
        generator = ffik.ManualTagVerificationThumbnail(
            tag=self,
            source=self.image.image_file
        )
        image = generator.generate()
        return image

    @property
    def delta_against_latest_analysis(self):
        return self.degrees - self.latest_analysis.orientation_from_moments

    @property
    def latest_analysis(self):
        return ImageAnalysis.objects.filter(
            image_id=self.image_id).order_by('analysis_datetime').last()

    @property
    def length(self):
        vector = np.array(self.int_start) - np.array(self.int_end)
        length = math.sqrt(np.sum(vector ** 2))
        return round(length, 2)


class EllipseSearchTag(models.Model):
    image = models.ForeignKey(Image)
    timestamp = models.DateTimeField('DTG of image capture', auto_now_add=True)
    start = models.CommaSeparatedIntegerField('the approximated arrow start',
                                              max_length=20)
    end = models.CommaSeparatedIntegerField('the approximated arrow end',
                                            max_length=20)

    @property
    def int_start(self):
        return tuple(int(x) for x in self.start.split(','))

    @property
    def int_end(self):
        return tuple(int(x) for x in self.end.split(','))

    @int_start.setter
    def int_start(self, value):
        self.start = ','.join(map(str, value))
        self.save()

    @int_end.setter
    def int_end(self, value):
        self.end = ','.join(map(str, value))
        self.save()

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

    @property
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


class AnalysisVerification(models.Model):
    image_analysis = models.ForeignKey(ImageAnalysis)
    timestamp = models.DateTimeField('DTG of analysis verification', auto_now_add=True)
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

    ordering = ['duration', 'voltage']

    @property
    def job_spec(self):
        return '_'.join(
            [
                str(x) for x in
                self.voltage, self.current, self.startup_delay, self.interval, self.duration
            ]
        )

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


class CaptureJobQueue(models.Model):
    name = models.CharField('name of the queue', max_length=50)
    timestamp = models.DateTimeField('when this queue was most recently saved', auto_now=True)
    queue = jsonfield.JSONField('a queue spec object')
    comment = models.TextField('description of this queue')


class KMeansEstimator(models.Model):
    timestamp = models.DateTimeField('when this estimator was produced', auto_now_add=True)

    estimator_params = jsonfield.JSONField('used to reconstruct the estimator')
    cluster_centers = jsonfield.JSONField('used to reconstruct the estimator')
    labels = jsonfield.JSONField('used to reconstruct the estimator')
    inertia = jsonfield.JSONField('used to reconstruct the estimator')

    scaler_params = jsonfield.JSONField('used to reconstruct scaler')
    scaler_mean = jsonfield.JSONField('used to reconstruct scaler')
    scaler_std = jsonfield.JSONField('used to reconstruct scaler')

    label_deltas = jsonfield.JSONField('a map from labels to deltas')

    comment = models.TextField('general comments about this estimator (optional)',
                               null=True, blank=True)

    metadata = jsonfield.JSONField('extra data about this stored estimator')

    @property
    def rebuilt_estimator(self):
        estimator = skc.KMeans()
        estimator.set_params(**self.estimator_params)
        estimator.cluster_centers_ = np.array(self.cluster_centers)
        estimator.labels_ = np.array(self.labels)
        estimator.inertia_ = self.inertia

        return estimator

    @property
    def rebuilt_scaler(self):
        scaler = skp.StandardScaler()
        scaler.set_params(**self.scaler_params)
        scaler.mean_ = np.array(self.scaler_mean)
        scaler.std_ = np.array(self.scaler_std)

        return scaler

    def extract_and_store_details_from_scaler(self, scaler):
        self.scaler_params = scaler.get_params()
        self.scaler_mean = scaler.mean_.tolist()
        self.scaler_std = scaler.std_.tolist()

    def extract_and_store_details_from_estimator(self, estimator):
        self.estimator_params = estimator.get_params()
        self.cluster_centers = estimator.cluster_centers_.tolist()
        self.labels = estimator.labels_.tolist()
        self.inertia = estimator.inertia_

    @property
    def label_deltas_defaultdict(self):
        return collections.defaultdict(int, self.label_deltas)


class ClassificationDeltaSet(models.Model):
    estimator = models.ForeignKey(KMeansEstimator)
    timestamp = models.DateTimeField('the datetime that this set of deltas was stored',
                                     auto_now_add=True)
    deltas = jsonfield.JSONField('the set of deltas')


class PriorityManualImage(models.Model):
    image = models.ForeignKey(Image)
    priority = models.IntegerField("the priority of this image for tagging (lower number means gets tagged sooner, default 5)", default=5)

    @classmethod
    def untagged_image(cls, payload):
        untagged_images = cls.objects.all()

        if untagged_images.count() == 0:
            return Image.untagged_image(payload)
        else:
            highest_priority = untagged_images.aggregate(ddm.Min('priority')).values()[0]
            untagged_image_ids = [x.id for x in untagged_images.filter(priority=highest_priority)]
            return {'id': random.choice(untagged_image_ids),
                    'valid': True}

@django.dispatch.dispatcher.receiver(ddms.post_delete, sender=Image)
def image_delete(sender, instance, **kwargs):
    # pass False so ImageField won't save the model
    instance.image_file.delete(False)


@django.dispatch.dispatcher.receiver(ddms.pre_delete, sender=ManualTag)
def tag_delete(sender, instance, **kwargs):
    instance.researcher.bad_tags += 1
    instance.researcher.save()

    instance.image.bad_tags += 1
    instance.image.save()
