import os
import datetime

import pytz


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
import djff.models as dm
import django.utils.timezone as dut
import django.shortcuts as ds

import celery
from djff.celery.django_celery import celery_app


@celery.shared_task(bind=True, name='results.debug_task')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@celery.shared_task(name='results.store_analyses')
def store_analyses(metas):
    # if we only have one meta, wrap it in a list
    if isinstance(metas, dict):
        metas = [metas]

    for meta in metas:
        # if we don't have an image ID in the metadata, there's not much use in proceeding
        try:
            image = dm.Image.objects.get(pk=int(meta['image_id']))
            del meta['image_id']
        except KeyError:
            raise AnalysisImportError('No image ID found in imported analysis metadata.')

        # remove the debugging and intermediate stuff that we don't need to keep
        for key in 'log all_contours'.split(' '):
            try:
                del meta[key]
            except KeyError:
                pass

        # translate the field names used during processing to the field names to store in the database
        analysis_config = {
            'analysis_datetime': 'timestamp',
            'silhouette': 'largest_contour',
            'hu_moments': 'hu_moments',
            'moments': 'moments',
        }
        for key, meta_key in analysis_config.iteritems():
            try:
                analysis_config[key] = meta[meta_key]
                del meta[meta_key]
            except KeyError:
                raise AnalysisImportError("Couldn't find '{}' in imported metadata.".format(meta_key))

            if 'ndarray' in str(analysis_config[key].__class__):
                analysis_config[key] = analysis_config[key].tolist()

            if key == 'hu_moments':
                analysis_config[key] = [x[0] for x in analysis_config[key]]

        analysis_config['analysis_datetime'] = datetime.datetime.utcfromtimestamp(
            float(analysis_config['analysis_datetime'])).replace(tzinfo=dut.utc)

        # whatever remains in the meta variable gets stored here
        analysis_config['meta_data'] = meta

        analysis = dm.ImageAnalysis(image=image, **analysis_config)

        return analysis.save()


@celery.shared_task(name='results.post_image')
def post_image(image_data, meta):
    xp = ds.get_object_or_404(dm.Experiment, pk=int(meta['xp_id']))

    image_config = dict()
    for key in 'cjr_id is_cal_image capture_timestamp voltage current'.split(' '):
        image_config[key] = meta[key]

    image = dm.Image(xp=xp, **image_config)
    image.image_file = image_data
    image.save()


@celery.shared_task(name='results.new_cjr')
def new_cjr(xp_id, voltage, current, start_timestamp):
    cjr = dm.CaptureJobRecord()

    cjr.xp_id = xp_id
    cjr.voltage = voltage
    cjr.current = current

    cjr.running = True

    cjr.job_start = datetime.datetime.utcfromtimestamp(
        float(start_timestamp)).replace(tzinfo=pytz.utc)

    cjr.save()

    return cjr.id


@celery.shared_task(name='results.job_status_report')
def job_status_report(status, start_timestamp, stop_timestamp, voltage, current, seconds_left,
                      xp_id, cjr_id, species, total, remaining):
    cjr = ds.get_object_or_404(dm.CaptureJobRecord, pk=int(cjr_id))

    cjr.running = (status == "running")

    cjr.job_start = dut.datetime.utcfromtimestamp(float(start_timestamp)).replace(tzinfo=dut.utc)

    if stop_timestamp:
        cjr.job_start = dut.datetime.utcfromtimestamp(
            float(start_timestamp)).replace(tzinfo=dut.utc)

    cjr.total = int(total)
    cjr.remaining = int(remaining)

    cjr.save()


@celery.shared_task(name='results.power_supply_report')
def power_supply_log(timestamp, voltage_meas, current_meas, extra_report_data=None):
    psl = dm.PowerSupplyLog()
    psl.measurement_datetime = dut.datetime.utcfromtimestamp(
        float(timestamp)).replace(tzinfo=dut.utc)
    psl.voltage_meas = voltage_meas
    psl.current_meas = current_meas
    psl.save()


class AnalysisImportError(Exception):
    pass