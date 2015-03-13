import os
import datetime

import celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
import django_fishface.djff.models as dm
import django.utils.timezone as dut
import django.shortcuts as ds

import util.fishface_config as ff_conf
from util.fishface_logging import logger


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


class AnalysisImportError(Exception):
    pass