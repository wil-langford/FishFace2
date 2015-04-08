import os
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lib.django.django_fishface.settings')
import lib.django.djff.models as dm
import django.db.models as ddm

from lib.fishface_image import FFImage
import celery
from lib.django_celery import celery_app

from lib.misc_utilities import chunkify

import etc.fishface_config as ff_conf
from lib.fishface_logging import logger


@celery.shared_task(name='django.ping')
def ping():
    return True


@celery.shared_task(bind=True, name='django.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


@celery.shared_task(name='django.analyze_images_from_cjr_list')
def analyze_images_from_cjr_list(cjr_ids):
    results = list()

    for cjr_id in cjr_ids:
        results.append(celery_app.send_task('django.analyze_images_from_cjr', args=(cjr_id,)))

    return results


@celery.shared_task(name='django.analyze_images_from_cjr')
def analyze_images_from_cjr(cjr_id):
    results = list()

    cjr = dm.CaptureJobRecord.objects.get(pk=cjr_id)
    cal_image = FFImage(source_filename=cjr.cal_image.image_file.path,
                        store_source_image_as='jpg')
    cjr_data = dm.Image.objects.filter(cjr_id=cjr.id)

    for chunk in chunkify(cjr_data, chunk_length=ff_conf.ML_STAGE_1_IMAGES_PER_CHUNK):
        data_list = [(datum.image_file.path, {'image_id': datum.id}) for datum in chunk]

        results.append(celery_app.send_task('django.analyze_image_list',
                                            args=(data_list, cal_image)))

    return results


@celery.shared_task(name='django.analyze_image_list')
def analyze_image_list(data_list, cal_image):
    return [
        celery.chain(
            celery_app.signature('drone.get_fish_contour', args=(FFImage(
                source_filename=filename, meta=meta), cal_image)),
            celery_app.signature('results.store_analyses')
        ).apply_async()
        for filename, meta in data_list
    ]


@celery.shared_task(name='django.train_classifier')
def train_classifier(minimum_verifications=ff_conf.ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1,
                     reserve_for_ml_verification=ff_conf.ML_RESERVE_DATA_FRACTION_FOR_VERIFICATION):
    eligible_image_ids = frozenset([i.id for i in dm.Image.objects.annotate(
        analysis_count=ddm.Count('imageanalysis')
    ).filter(
        analysis_count__gte=1
    )])

    eligible_tags = random.shuffle(list(
        dm.ManualTag.objects.annotate(
            verify_count=ddm.Count('manualverification'),
        ).filter(
            verify_count__gte=minimum_verifications,
            image_id__in=eligible_image_ids
        )
    ))

    if eligible_tags:
        split_point = int(float(len(eligible_tags)) * reserve_for_ml_verification)
    else:
        logger.warning("No eligible tags found during classifier training.")
        return False

    verification_set, training_set = eligible_tags[:split_point], eligible_tags[split_point:]

    return verification_set, training_set



class AnalysisImportError(Exception):
    pass