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
    return [celery_app.send_task('django.analyze_images_from_cjr', args=(cjr_id,))
            for cjr_id in cjr_ids]


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


@celery.shared_task(name='django.training_eligible_data')
def training_eligible_data(
        minimum_verifications=ff_conf.ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1):
    analyzed_image_ids = frozenset([i.id for i in dm.Image.objects.annotate(
        analysis_count=ddm.Count('imageanalysis')
    ).filter(
        analysis_count__gte=1
    )])

    if analyzed_image_ids:
        logger.debug('found {} analyzed image IDs'.format(len(analyzed_image_ids)))
    else:
        logger.warning('Found no analyzed images.')
        return False

    eligible_tags = list(
        dm.ManualTag.objects.annotate(
            verify_count=ddm.Count('manualverification'),
        ).filter(
            verify_count__gte=minimum_verifications,
            image_id__in=analyzed_image_ids
        )
    )
    random.shuffle(eligible_tags)

    if eligible_tags:
        logger.debug('found {} eligible tags'.format(len(eligible_tags)))
        data = list()

        for tag in eligible_tags:
            # finding this is relatively expensive, so let's name it locally
            tag_latest_analysis = tag.latest_analysis
            data.append({
                'analysis_id': tag_latest_analysis.id,
                'hu_moments': tag_latest_analysis.hu_moments,
                'delta': tag.degrees - tag_latest_analysis.orientation_from_moments,
            })

        return data
    else:
        logger.warning("No eligible tags found.")
        return False


@celery.shared_task(name='django.create_and_store_estimator')
def create_and_store_estimator(ted):
    return (
        celery.signature('learn.create_estimator', args=(ted,)) |
        celery.signature('results.store_estimator')
    ).apply_async()


@celery.shared_task(name='django.create_and_store_estimator_from_all_eligible_data')
def create_and_store_estimator_from_all_eligible(
        minimum_verifications=ff_conf.ML_MINIMUM_TAG_VERIFICATIONS_DURING_STAGE_1):
        return (
            celery.signature('django.training_eligible_data',
                             args=(minimum_verifications,)) |
            celery.signature('learn.create_estimator') |
            celery.signature('results.store_estimator')
        ).apply_async()


@celery.shared_task(name='django.automatically_tag_with_stored_estimator')
def automatically_tag_with_stored_estimator(all_analysis_ids, stored_estimator_id):
    for analysis_ids in chunkify(all_analysis_ids, 100):
        analyses = [(
            analysis.id,
            analysis.hu_moments,
            analysis.centroid,
            analysis.orientation_from_moments,
        ) for analysis in dm.ImageAnalysis.objects.filter(id__in=analysis_ids)]

        estimator_object = dm.KMeansEstimator.objects.get(pk=stored_estimator_id)

        estimator = estimator_object.rebuilt_estimator
        scaler = estimator_object.rebuilt_scaler
        label_deltas = estimator_object.label_deltas_defaultdict

        (
            celery.signature('drone.compute_automatic_tags_with_estimator',
                                 args=(analyses, estimator, scaler, label_deltas)) |
            celery.signature('results.store_automatic_analysis_tags')
        ).apply_async()


@celery.shared_task(name='django.automatically_tag_by_ellipse_search')
def automatically_tag_by_ellipse_search(all_image_ids):
    for image_ids in chunkify(all_image_ids, 10):
        taggable = list()
        cals = dict()
        for image in list(dm.ImageAnalysis.objects.filter(id__in=image_ids)):
            with open(image.image_file.file.name, 'rb') as data_file:
                data = data_file.read()

            cal_name = image.cjr.cal_image.image_file.file.name
            if cal_name not in cals:
                with open(cal_name, 'rb') as cal_file:
                    cals[cal_name] = cal_file.read()

            taggable.append((
                image.id,
                data,
                cal_name,
                image.cjr.search_min,
                image.cjr.search_max
            ))

        (
            celery.signature('drone.compute_automatic_tags_with_ellipse_search',
                                 args=(taggable, cals)) |
            celery.signature('results.store_ellipse_search_tags')
        ).apply_async()


@celery.shared_task(name='django.update_ellipse_parameters_with_tag')
def update_ellipse_parameters_with_tag(tag_id, radius_of_roi=100):
    tag = dm.ManualTag.objects.get(pk=tag_id)
    with open(tag.image.image_file.file.name, 'rb') as data_file:
        data = data_file.read()
    with open(tag.image.cjr.cal_image.image_file.file.name, 'rb') as cal_file:
        cal = cal_file.read()

    return (tag_id, data, cal, tag.int_start, tag.degrees, radius_of_roi)


class AnalysisImportError(Exception):
    pass