import os

import cv2

import numpy as np

import fishface_image
from fishface_image import FFImage, ff_operation, ff_annotation
import celery
import fishface_celery
from scipy import ndimage
from scipy import stats

celery_app = fishface_celery.app

HOME = os.path.expanduser('~')
ALT_ROOT = HOME

#
# Convenience functions
#


def kernel(radius=3, shape='circle'):
    if isinstance(shape, basestring):
        shape = {
            'circle': cv2.MORPH_ELLIPSE,
            'cross': cv2.MORPH_CROSS,
            'rect': cv2.MORPH_RECT,
            'rectangle': cv2.MORPH_RECT,
        }[shape]
    return cv2.getStructuringElement(shape, (radius * 2 + 1, radius * 2 + 1))


@celery_app.task
def return_passthrough(*args, **kwargs):
    return {'args': args, 'kwargs': kwargs}


def test_write_image(ff_image):
    full_path = os.path.join(ALT_ROOT, 'test_out', ff_image.meta['filename'])
    cv2.imwrite(full_path, ff_image.array)


def image_from_file(file_path):
    return FFImage(cv2.imread(file_path, 0))


@ff_operation
def delta_image(image, cal_image, ff_image=None):
    if isinstance(cal_image, FFImage):
        ff_image.log = ('cal_image.meta', cal_image.meta)
        cal_image = cal_image.array
    if not isinstance(cal_image, np.ndarray):
        raise TypeError('cal_image must be an FFImage or numpy array')

    # adjustment for overall brightness delta
    delta_mode = stats.mstats.mode(image.astype(np.int16) - cal_image.astype(np.int16), axis=None)
    almost_there = cv2.absdiff(cal_image, image).astype(np.int16) + delta_mode[0][0]
    almost_there[almost_there < 0] = 0
    return almost_there.astype(np.uint8)


@ff_operation
def threshold_by_type(image, thresh=None, otsu=True, ff_image=None, thresh_type=cv2.THRESH_BINARY):
    if thresh is None:
        if not otsu:
            raise TypeError('Either otsu must be true or thresh must be specified.')
        thresh = 0

    thresh, im = cv2.threshold(src=image,
                               thresh=thresh * int(not otsu),
                               maxval=255,
                               type=thresh_type + (cv2.THRESH_OTSU * int(otsu)))

    ff_image.log = 'thresh:{}'.format(thresh)

    return im


@ff_operation
def adaptive_threshold(image, block_size=7, constant_adjustment=0):
    return cv2.adaptiveThreshold(src=image,
                                 maxValue=255,
                                 adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 blockSize=block_size,
                                 C=constant_adjustment,
                                 thresholdType=cv2.THRESH_BINARY)


@ff_operation
def erode(image, kernel_radius=3, kernel_shape='circle', iterations=1, ff_image=None):
    return cv2.erode(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


@ff_operation
def dilate(image, kernel_radius=3, kernel_shape='circle', iterations=1, ff_image=None):
    return cv2.dilate(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


def opening(ff_image, **kwargs):
    erode(ff_image, **kwargs)
    dilate(ff_image, **kwargs)


def closing(ff_image, **kwargs):
    dilate(ff_image, **kwargs)
    erode(ff_image, **kwargs)


@ff_operation
def distance_transform(image, ff_image=None):
    return cv2.distanceTransform(image, cv2.cv.CV_DIFF_L2, cv2.cv.CV_DIST_MASK_PRECISE)


@ff_operation
def canny(image, threshold1=50, threshold2=100, aperture_size=3, ff_image=None):
    return cv2.Canny(image,
                     threshold1=threshold1,
                     threshold2=threshold2,
                     apertureSize=aperture_size)


def return_cropped(ff_image, box):
    """Crops the image to the box provided."""
    image = ff_image.array
    ff_image.log = 'OP: crop'
    ff_image.log = 'cropped to: ({}, {}):({}, {})'.format(*box)
    return image[box[0]:box[2], box[1]:box[3]]


@ff_annotation
def annotate_all_contours(image, ff_image=None):
    all_contours = cv2.findContours(image,
                                    mode=cv2.RETR_EXTERNAL,
                                    method=cv2.CHAIN_APPROX_SIMPLE
                                    )[0]
    if all_contours is None or len(all_contours) == 0:
        all_contours = False

    ff_image.meta['all_contours'] = all_contours

    return all_contours


@ff_annotation
def annotate_largest_contour(image, ff_image=None):
    all_contours = getattr(ff_image.meta, 'all_contours', None)
    if all_contours is None:
        ff_image.log = "lazy all contours annotation"
        all_contours = annotate_all_contours(ff_image)

    if all_contours is False:
        ff_image.meta['largest_contour'] = False
        return

    areas = [cv2.contourArea(ctr) for ctr in all_contours]

    max_contour = all_contours[areas.index(max(areas))]

    ff_image.meta['largest_contour'] = max_contour
    ff_image.meta['largest_contour_bounding_box'] = bounding_box_from_contour(ff_image,
                                                                              max_contour)
    del ff_image.meta['all_contours']

    return max_contour


@ff_annotation
def annotate_moments(image, ff_image=None):
    largest_contour = getattr(ff_image.meta, 'largest_contour', None)
    if largest_contour is None:
        ff_image.log = "lazy largest contour annotation"
        largest_contour = annotate_largest_contour(ff_image)

    if largest_contour is not False:
        moments = cv2.moments(largest_contour)
    else:
        moments = False

    ff_image.meta['moments'] = moments

    return moments


@ff_annotation
def annotate_hu_moments(image, ff_image=None):
    moments = getattr(ff_image.meta, 'moments', None)
    if moments is None:
        ff_image.log = "lazy moment annotation"
        moments = annotate_moments(ff_image)

    if moments is not False:
        hu_moments = cv2.HuMoments(moments)
    else:
        hu_moments = False

    ff_image.meta['hu_moments'] = hu_moments

    return hu_moments


def bounding_box_from_contour(ff_image, contour, border=1):
    """Convenience method to find the bounding box of a contour. Output is a tuple
    of the form (y_min, x_min, y_max, x_max).  The border is an optional extra
    margin to include in the cropped image."""

    image_shape = ff_image.array.shape

    x_corner, y_corner, width, height = cv2.boundingRect(contour)

    x_min = max(0, x_corner - border)
    y_min = max(0, y_corner - border)
    x_max = min(image_shape[1] - 1, x_corner + width + border)
    y_max = min(image_shape[0] - 1, y_corner + height + border)

    return (y_min, x_min, y_max, x_max)


@ff_operation
def draw_contours(image, contours, line_color=255, line_thickness=3, filled=True,
                  ff_image=None):
    """Actually draws the provided contours onto the image."""

    if filled:
        line_thickness = -abs(line_thickness)

    cv2.drawContours(image=image,
                     contours=contours,
                     contourIdx=-1,
                     color=line_color,
                     thickness=line_thickness)

    return image


@celery_app.task
def test_get_fish_silhouettes(test_data_dir='test_data_dir'):
    data_dir = os.path.join(ALT_ROOT, test_data_dir)

    cal_image = FFImage(source_filename='XP-23_CJR-0_HP_2015-01-20-221120_1421791881.65.jpg',
                        source_dir=data_dir)

    files = [name for name in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir,name))]
    data = [name for name in files if ('XP-23_CJR' in name and 'CJR-0' not in name)]

    return celery.chord(get_fish_contour.s(FFImage(source_filename=datum,
                                                   source_dir=data_dir,
                                                   store_source_image_as='jpg'),
                                           cal_image)
                        for datum in data)(return_passthrough.s())


@celery_app.task
def get_fish_contour(data, cal):

    color_image = cv2.cvtColor(data.array, cv2.COLOR_GRAY2BGR)

    delta_image(data, cal)
    threshold_by_type(data)
    erode(data)
    distance_transform(data)
    threshold_by_type(data, otsu=False, thresh=5)

    markers = data.array.copy()
    dilate(data, iterations=7)
    border = data.array.copy()
    border = border - cv2.erode(border, None)

    markers, num_blobs = ndimage.measurements.label(markers)
    markers[border == 255] = 255

    markers = markers.astype(np.int32)
    cv2.watershed(image=color_image, markers=markers)
    markers[markers == -1] = 0
    markers = 255 - markers.astype(np.uint8)

    image = FFImage(markers, meta=data.meta, log=data.log)

    annotate_hu_moments(image)

    return image.meta



def test_normalize_test_data(test_data_dir='test_data_dir'):
    data_dir = os.path.join(ALT_ROOT, test_data_dir)

    data = [name for name in os.listdir(data_dir) if
            'CJR-0' in name and os.path.isfile(os.path.join(data_dir, name))]

    for jpeg_filename in data:
        image = cv2.imread(os.path.join(data_dir, jpeg_filename))
        ff_image = FFImage(image)
        ff_image.meta['filename'] = jpeg_filename
        test_write_image(ff_image)


class ImageProcessingException(Exception):
    pass