import os

import cv2

import numpy as np

import fishface_image
from fishface_image import FFImage, ff_operation, ff_annotation
import celery
import fishface_celery

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


def decode_jpeg_string(jpeg_string):
    jpeg_array = np.fromstring(jpeg_string, dtype=np.uint8)
    return FFImage(cv2.imdecode(jpeg_array, 0))


@ff_operation
def delta_image(image, cal_image, ff_image=None):
    if isinstance(cal_image, FFImage):
        ff_image.log = ('cal_image.meta', cal_image.meta)
        cal_image = cal_image.array
    if not isinstance(cal_image, np.ndarray):
        raise TypeError('cal_image must be an FFImage or numpy array')

    return cv2.absdiff(cal_image, image)


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

    ff_image.log = 'threshed with {}'.format(thresh)

    return im


def threshold_band_pass(ff_image, min_thresh=None, max_thresh=None, min_otsu=True, max_otsu=True):
    if min_thresh is not None or min_otsu:
        min_thresh = 0
    else:
        raise TypeError('Either otsu must be true or min_thresh must be specified.')

    if max_thresh is not None or max_otsu:
        max_thresh = 255
    else:
        raise TypeError('Either otsu must be true or max_thresh must be specified.')

    threshold_by_type(ff_image, thresh=min_thresh, otsu=min_otsu, thresh_type=cv2.THRESH_TRUNC)
    threshold_by_type(ff_image, thresh=max_thresh, otsu=max_otsu, thresh_type=cv2.THRESH_TOZERO_INV)
    threshold_by_type(ff_image, thresh=min_thresh, otsu=min_otsu, thresh_type=cv2.THRESH_BINARY)

    ff_image.log = 'threshed with {}'.format((min_thresh, max_thresh))

    return ff_image


@ff_operation
def adaptive_threshold(image, block_size=7, constant_adjustment=0):
    return cv2.adaptiveThreshold(src=image,
                                 maxValue=255,
                                 adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 blockSize=block_size,
                                 C=constant_adjustment,
                                 thresholdType=cv2.THRESH_BINARY)


@ff_operation
def erode(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.erode(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


@ff_operation
def dilate(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.dilate(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


@ff_operation
def opening(image, **kwargs):
    return dilate(erode(image, **kwargs), **kwargs)


@ff_operation
def canny(image, threshold1=50, threshold2=100, aperture_size=3, ff_image=None):
    return cv2.Canny(image,
                     threshold1=threshold1,
                     threshold2=threshold2,
                     apertureSize=aperture_size)


@ff_operation
def closing(image, **kwargs):
    return erode(dilate(image, **kwargs), **kwargs)


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
        ff_image.meta['all_contours'] = 'NO_CONTOURS'
    else:
        ff_image.meta['all_contours'] = all_contours


@ff_annotation
def annotate_largest_contour(image, ff_image=None):
    all_contours = getattr(ff_image.meta, 'all_contours', None)
    if all_contours is None:
        annotate_all_contours(ff_image)
        all_contours = ff_image.meta['all_contours']

    if all_contours == 'NO_CONTOURS':
        raise ImageProcessingException("No contours found in image.")

    areas = [cv2.contourArea(ctr) for ctr in all_contours]

    max_contour = all_contours[areas.index(max(areas))]

    ff_image.meta['largest_contour'] = max_contour
    ff_image.meta['largest_contour_bounding_box'] = bounding_box_from_contour(ff_image,
                                                                             max_contour)


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
def draw_contours(image, contours, line_color=(255, 0, 255), line_thickness=3, filled=True,
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


def test_get_fish_silhouettes(test_data_dir='test_data_dir'):
    data_dir = os.path.join(ALT_ROOT, test_data_dir)

    def ff_jpeg_loader(data_filename):
        with open(os.path.join(data_dir, data_filename), 'rb') as jpeg_file:
            jpeg = jpeg_file.read()
            jpeg_image = decode_jpeg_string(jpeg)
            jpeg_image.meta['filename'] = data_filename
        return jpeg_image

    cal_image = ff_jpeg_loader('XP-23_CJR-0_HP_2015-01-20-221120_1421791881.65.jpg')

    data = [name for name in os.listdir(data_dir) if ('XP-23_CJR' in name and
                                                      'CJR-0' not in name and
                                                      os.path.isfile(os.path.join(data_dir, name)))
    ]

    return celery.chord(get_single_fish_silhouette.s(ff_jpeg_loader(datum), cal_image)
                        for datum in data)(return_passthrough.s())


@celery_app.task
def get_single_fish_silhouette(data, cal):
    delta_image(data, cal)
    threshold_band_pass(data, max_thresh=100, max_otsu=False)
    canny(data)
    annotate_largest_contour(data)
    return data


class ImageProcessingException(Exception):
    pass


def test_normalize_test_data(test_data_dir='test_data_dir'):
    data_dir = os.path.join(ALT_ROOT, test_data_dir)

    data = [name for name in os.listdir(data_dir) if
            'CJR-0' in name and os.path.isfile(os.path.join(data_dir, name))]

    for jpeg_filename in data:
        image = cv2.imread(os.path.join(data_dir, jpeg_filename))
        ff_image = FFImage(input_array=image)
        ff_image.meta['filename'] = jpeg_filename
        test_write_image(ff_image)

