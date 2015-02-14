import os
import functools

import cv2

import numpy as np

import fishface_image
from fishface_image import FFImage, ff_image_wrapper
import celery
import fishface_celery

celery_app = fishface_celery.app


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
def dummy_returner(*args, **kwargs):
    return (args, kwargs)


def write_test_file_by_name(filename):
    full_path = os.path.join('/home/wsl/test_out', filename)
    with open(full_path, 'wt') as file_handle:
        file_handle.write("I'm a good worker and I'm writing to filename {}!\n".format(filename))

    return full_path


def image_from_file(file_path):
    return FFImage(cv2.imread(file_path, 0))


def decode_jpeg_string(jpeg_string):
    jpeg_array = np.fromstring(jpeg_string, dtype=np.uint8)
    return FFImage(cv2.imdecode(jpeg_array, 0))


@ff_image_wrapper
def delta_image(image, cal_image, ffimage=None):
    if isinstance(cal_image, FFImage):
        ffimage.log = ('cal_image.meta', cal_image.meta)
        cal_image = cal_image.array
    if not isinstance(cal_image, np.ndarray):
        raise TypeError('cal_image must be an FFImage or numpy array')

    return cv2.absdiff(cal_image, image)


@ff_image_wrapper
def threshold(image, thresh=None, otsu=True, ffimage=None):
    if thresh is None:
        if not otsu:
            raise TypeError('Either otsu must be true or thresh must be specified.')
        thresh = 0

    thresh, im = cv2.threshold(src=image,
                               thresh=thresh * int(not otsu),
                               maxval=255,
                               type=cv2.THRESH_BINARY + (cv2.THRESH_OTSU * int(otsu)))
    ffimage.log = 'threshed with {}'.format(thresh)

    return im


@ff_image_wrapper
def adaptive_threshold(image, block_size=7, C=0):
    return cv2.adaptiveThreshold(src=image,
                                 maxValue=255,
                                 adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 blockSize=block_size,
                                 C=C,
                                 thresholdType=cv2.THRESH_BINARY)


@ff_image_wrapper
def erode(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.erode(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


@ff_image_wrapper
def dilate(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.dilate(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


@ff_image_wrapper
def opening(image, **kwargs):
    return dilate(erode(image, **kwargs), **kwargs)


@ff_image_wrapper
def closing(image, **kwargs):
    return erode(dilate(image, **kwargs), **kwargs)


def return_cropped(ffimage, box):
    """Crops the image to the box provided."""
    image = ffimage.array
    ffimage.log = 'OP: crop'
    ffimage.log = 'cropped to: ({}, {}):({}, {})'.format(*box)
    return image[box[0]:box[2], box[1]:box[3]]


@celery_app.task
def normalize_to_largest_blob(ffimage):
    contours = find_all_contours(ffimage.array)
    areas = [cv2.contourArea(ctr) for ctr in contours]
    if len(areas):
        max_contour = contours[areas.index(max(areas))]
        ffimage.meta['largest_blob_contour'] = max_contour
        draw_contours(ffimage.array, [max_contour])

        bounding_box = bounding_box_from_contour(ffimage.array.shape, max_contour)
        image = return_cropped(ffimage, bounding_box)

        return image, ffimage.meta, ffimage.log
    else:
        raise Exception("No contours found in this frame.")


def find_all_contours(input_image):
    if isinstance(input_image, FFImage):
        image = input_image.array
    elif isinstance(input_image, np.ndarray):
        image = input_image
    else:
        raise fishface_image.InvalidSourceArray('Argument must be a numpy array or an FFImage.')

    return cv2.findContours(image,
                            mode=cv2.RETR_EXTERNAL,
                            method=cv2.CHAIN_APPROX_SIMPLE
                            )[0]


def bounding_box_from_contour(image_shape, contour, border=1):
    """Convenience method to find the bounding box of a contour. Output is a tuple
    of the form (y_min, x_min, y_max, x_max).  The border is an optional extra
    margin to include in the cropped image."""

    x_corner, y_corner, width, height = cv2.boundingRect(contour)

    x_min = max(0, x_corner - border)
    y_min = max(0, y_corner - border)
    x_max = min(image_shape[1] - 1, x_corner + width + border)
    y_max = min(image_shape[0] - 1, y_corner + height + border)

    return (y_min, x_min, y_max, x_max)


def draw_contours(image, contours, line_color=(255, 0, 255), line_thickness=3, filled=True):
    """Actually draws the provided contours onto the image."""

    if filled:
        line_thickness = -abs(line_thickness)

    cv2.drawContours(image=image,
                     contours=contours,
                     contourIdx=-1,
                     color=line_color,
                     thickness=line_thickness)


def test_get_fish_silhouettes():
    data_dir = '/home/wsl/2015.01.20'

    def ff_jpeg_loader(name):
        with open('{}/{}'.format(data_dir, name), 'rb') as jpeg_file:
            jpeg = jpeg_file.read()
            jpeg_image = decode_jpeg_string(jpeg)
            jpeg_image.meta['filename'] = name
        return (jpeg, jpeg_image)

    cal_jpeg, cal_image = ff_jpeg_loader('XP-23_CJR-0_HP_2015-01-20-221120_1421791881.65.jpg')

    sil = get_single_fish_silhouette.s(cal_image)

    data = [name for name in os.listdir(data_dir) if
             'CJR-0' not in name and os.path.isfile(os.path.join(data_dir, name))]

    return celery.chord([(datum, sil(ff_jpeg_loader(datum)[1])) for datum in data])(dummy_returner.s())


@celery_app.task
def get_single_fish_silhouette(data, cal):
    delta_image(data, cal)
    threshold(data)
    return normalize_to_largest_blob(data)