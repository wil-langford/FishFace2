from __future__ import absolute_import
import celery
import djff.models as dm

import cv2

NORMALIZED_SHAPE = (512, 384)


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


@celery.shared_task
def store_analysis(meta):
    # if we don't have an image ID in the metadata, there's not much use in proceeding
    try:
        image = dm.Image.objects.get(pk=meta['image_id'])
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