import os
import random

import celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_fishface.settings')
import django_fishface.djff.models as dm
import django.db.models as ddm

from util.fishface_image import FFImage
from ff_celery.fishface_celery import celery_app


# used for testing
@celery.shared_task(name='django.return_passthrough')
def return_passthrough(*args, **kwargs):
    return {'args': args, 'kwargs': kwargs}


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
def train_classifier(minimum_verifications=2, reserve_for_ml_verification=0.1):
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