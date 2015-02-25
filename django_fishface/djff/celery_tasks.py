import os
import sys

import celery
import models as dm

from django.conf import settings

import cv2

HOME = os.environ['HOME']
ALT_ROOT = HOME
CLUSTER_DIR = os.path.join(ALT_ROOT, 'FishFace2', 'cluster')
CELERY_WORKER_DIR = os.path.join(CLUSTER_DIR, 'celery_worker')

# TODO: replace this antipattern
import site
site.addsitedir(CLUSTER_DIR)
site.addsitedir(CELERY_WORKER_DIR)
import celery_worker.tasks as worker_tasks
from celery_worker.fishface_image import FFImage, NORMALIZED_DTYPE, NORMALIZED_SHAPE
from celery_worker.fishface_celery import app as celery_app

print ("= " * 40 + '\n') * 4
print sys.path
print ("= " * 40 + '\n') * 4

# used for testing
@celery.shared_task
def return_passthrough(*args, **kwargs):
    return {'args': args, 'kwargs': kwargs}


def normalize_array(image):
    if image.shape == NORMALIZED_SHAPE:
        return image

    # too many color channels
    if len(image.shape) == 3:
        channels = image.shape[2]
        if channels == 3:
            conversion = cv2.COLOR_BGR2GRAY
        elif channels == 4:
            conversion = cv2.COLOR_BGRA2GRAY
        else:
            raise Exception("Why do I see {} color channels? ".format(channels) +
                            "I can only handle 1, 3, or 4 (with alpha).")

        image = cv2.cvtColor(image, conversion)

    if image.shape != NORMALIZED_SHAPE:
        image = cv2.resize(image,
                           dsize=tuple(reversed(NORMALIZED_SHAPE)),
                           interpolation=cv2.INTER_AREA)
    return image


def cjr_boomerang(cjr_id=1):
    cjr = dm.CaptureJobRecord.objects.get(pk=cjr_id)
    cal_image = FFImage(source_filename=cjr.cal_image.image_file.path, store_source_image_as='jpg')
    cjr_data = dm.Image.objects.filter(cjr_id=cjr.id)
    ff_images = (
        FFImage(source_filename=datum.image_file.path,
                meta={'image_id': datum.id})
        for datum in cjr_data
    )

    # metas = celery_app.send_task('tasks.test_get_fish_silhouettes').get().get()['args'][0]

    return celery.chord(
        celery_app.signature('django.drone_tasks.get_fish_contour', (im, cal_image))
        for im in ff_images
    )(
        celery_app.signature('fishface.django_tasks.store_analyses', tuple())
    )


@celery_app.task(name='fishface.django_tasks.store_analyses')
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
        for key, meta_key in analysis_config:
            try:
                analysis_config[key] = meta[meta_key]
                del meta[meta_key]
            except KeyError:
                raise AnalysisImportError("Couldn't find '{}' in imported metadata.".format(meta_key))

        # whatever remains in the meta variable gets stored here
        analysis_config['meta_data'] = meta

        analysis = dm.ImageAnalysis(image=image, **analysis_config)
        analysis.save()

class AnalysisImportError(Exception):
    pass