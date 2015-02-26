import os
import datetime

import celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
from django.conf import settings
import models as dm
import django.utils.timezone as dut

HOME = os.environ['HOME']
ALT_ROOT = HOME

from fishface_image import FFImage
from fishface_celery import app as celery_app


# used for testing
@celery.shared_task(name='results.return_passthrough')
def return_passthrough(*args, **kwargs):
    return {'args': args, 'kwargs': kwargs}


def cjr_boomerang(cjr_id=1):
    cjr = dm.CaptureJobRecord.objects.get(pk=cjr_id)
    cal_image = FFImage(source_filename=cjr.cal_image.image_file.path, store_source_image_as='jpg')
    cjr_data = dm.Image.objects.filter(cjr_id=cjr.id)
    ff_images = [
        FFImage(source_filename=datum.image_file.path,
                meta={'image_id': datum.id})
        for datum in cjr_data
    ][:2]

    # metas = celery_app.send_task('tasks.test_get_fish_silhouettes').get().get()['args'][0]

    results = list()
    for ff_image in ff_images:
        results.append(
            celery.chain(celery_app.signature('tasks.get_fish_contour',
                                              args=(ff_image, cal_image),
                                              options={'queue': 'tasks'}),
                         celery_app.signature('results.store_analyses',
                                              options={'queue': 'results'}),
                         ).apply_async()
        )

    return results

@celery_app.task(name='results.store_analyses')
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

        analysis_config['analysis_datetime'] = datetime.datetime.utcfromtimestamp(
            float(analysis_config['analysis_datetime'])).replace(tzinfo=dut.utc)

        # whatever remains in the meta variable gets stored here
        analysis_config['meta_data'] = meta

        analysis = dm.ImageAnalysis(image=image, **analysis_config)
        analysis.save()

class AnalysisImportError(Exception):
    pass