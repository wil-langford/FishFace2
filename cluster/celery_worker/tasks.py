import os

import cv2
import cv2.cv as cv

import numpy as np

import fishface_image
import fishface_celery

celery_app = fishface_celery.app


@celery_app.task
def dummy_returner(*args, **kwargs):
    return (args, kwargs)


def write_test_file_by_name(filename):
    full_path = os.path.join('/home/wsl/test_out', filename)
    with open(full_path, 'wt') as file_handle:
        file_handle.write("I'm a good worker and I'm writing to filename {}!\n".format(filename))

    return full_path


def image_from_file(file_path):
    return array_to_ffarray(cv2.imread(file_path, 0))


def decode_jpeg_string(jpeg_string):
    jpeg_array = np.fromstring(jpeg_string, dtype=np.uint8)
    return array_to_ffarray(cv2.imdecode(jpeg_array, 0))


def normalize_image(image):
    if image.shape == (384, 512):
        return image

    # too many color channels
    if len(image.shape) == 3:
        channels = image.shape[2]
        if channels == 3:
            conversion = cv.CV_BGR2GRAY
        elif channels == 4:
            conversion = cv.CV_BGRA2GRAY
        else:
            raise Exception("Why do I see {} color channels? ".format(channels) +
                            "I can only handle 1, 3, or 4 (with alpha).")

        image = cv2.cvtColor(image, conversion)

    s_image = cv2.resize(image, dsize=(512, 384), interpolation=cv.CV_INTER_AREA)
    return s_image


def delta_image(image, cal_image):
    image = normalize_image(image)
    cal_image = normalize_image(cal_image)

    return cv2.absdiff(cal_image, image)


def threshold(image, thresh):
    return cv2.threshold(src=image,
                         thresh=thresh,
                         maxval=255,
                         type=cv2.THRESH_BINARY)[1]


def kernel(radius=3, shape='circle'):
    if isinstance(shape, basestring):
        shape = {
            'circle': cv2.MORPH_ELLIPSE,
            'cross': cv2.MORPH_CROSS,
            'rect': cv2.MORPH_RECT,
            'rectangle': cv2.MORPH_RECT,
        }[shape]
    return cv2.getStructuringElement(shape, (radius * 2 + 1, radius * 2 + 1))


def erode(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.erode(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


def dilate(image, kernel_radius=3, kernel_shape='circle', iterations=1):
    return cv2.dilate(src=image, kernel=kernel(kernel_radius, kernel_shape), iterations=iterations)


def opening(image, **kwargs):
    return dilate(erode(image, **kwargs), **kwargs)


def closing(image, **kwargs):
    return erode(dilate(image, **kwargs), **kwargs)


def set_largest_blob(image):
    contours = find_all_contours()
    areas = [cv2.contourArea(ctr) for ctr in contours]
    if len(areas):
        max_contour = contours[areas.index(max(areas))]
        add_contours_to(image, [max_contour])

        bounding_box = bounding_box_from_contour(image, max_contour)
        image = apply_crop(image, bounding_box)

        image.meta['moments'] = cv2.moments(image)
    else:
        raise Exception("No contours found in this frame.")


def find_all_contours(image):
    return cv2.findContours(image.array,
                            mode=cv2.RETR_EXTERNAL,
                            method=cv2.CHAIN_APPROX_SIMPLE
                            )[1]


def bounding_box_from_contour(image, contour, border=1):
    """Convenience method to find the bounding box of a contour. Output is a tuple
    of the form (y_min, x_min, y_max, x_max).  The border is an optional extra
    margin to include in the cropped image."""

    x_corner, y_corner, width, height = cv2.boundingRect(contour)

    x_min = max(0, x_corner - border)
    y_min = max(0, y_corner - border)
    x_max = min(image.height - 1, x_corner + width + border)
    y_max = min(image.width - 1, y_corner + height + border)

    return (y_min, x_min, y_max, x_max)


def add_contours_to(image, contours, line_color=(255, 0, 255), line_thickness=3, filled=True):
    """Actually draws the provided contours onto the image."""

    if filled:
        line_thickness = -abs(line_thickness)

    cv2.drawContours(image=image,
                     contours=contours,
                     contourIdx=-1,
                     color=line_color,
                     thickness=line_thickness)


def apply_crop(image, box):
    """Crops the image to the box provided."""

    # save the last shape and the bounding box for future reference
    image.meta['last_shape'] = image.meta['shape']

    if 'cropped_to' in image.meta:
        sct = image.meta['cropped_to']
        add_me = (sct[0], sct[1], sct[0], sct[1])
        image.meta['cropped_to'] = [a + b for a, b in zip(box, add_me)]
    else:
        image.meta['cropped_to'] = box

    if 'centroid' in image.meta:
        sct = image.meta['cropped_to']
        add_me = (sct[0], sct[1])
        image.meta['centroid'] = (image.meta['centroid'][0] + add_me[0],
                                  image.meta['centroid'][1] + add_me[1])

    return image[box[0]:box[2], box[1]:box[3]]

chainProcessList = [
    ('deltaImage', {}),
    ('grayImage', {}),
    ('threshold', {}),
    ('closing', {}),
    ('opening', {}),
    ('cropToLargestBlob', {}),
    ('findCentroid', {})
]
