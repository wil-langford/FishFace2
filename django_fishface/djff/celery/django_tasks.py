import os
import random

import celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
import django_fishface.djff.models as dm
import django.db.models as ddm

from util.fishface_image import FFImage
from ff_celery.fishface_celery import celery_app

import util.fishface_config as ff_conf


@celery_app.task(bind=True, name='django.debug_task')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@celery.shared_task(name='django.analyze_cjr_images')
def analyze_cjr_images(cjr_ids):
    results = list()

    if not isinstance(cjr_ids, (list, tuple)):
        cjr_ids = [cjr_ids]

    for cjr_id in cjr_ids:
        cjr = dm.CaptureJobRecord.objects.get(pk=cjr_id)
        cal_image = FFImage(source_filename=cjr.cal_image.image_file.path,
                            store_source_image_as='jpg')
        cjr_data = dm.Image.objects.filter(cjr_id=cjr.id)
        ff_images = [
            FFImage(source_filename=datum.image_file.path,
                    meta={'image_id': datum.id})
            for datum in cjr_data
        ]

        for ff_image in ff_images:
            results.append(
                celery.chain(
                    celery_app.signature('drone.get_fish_contour', args=(ff_image, cal_image)),
                    celery_app.signature('results.store_analyses')
                ).apply_async()
            )

    return results


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

    split_point = int(float(len(eligible_tags)) * reserve_for_ml_verification)

    verification_set, training_set = eligible_tags[:split_point], eligible_tags[split_point:]


class AnalysisImportError(Exception):
    pass