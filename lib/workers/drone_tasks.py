import time

import cv2
import math
import numpy as np
from scipy import ndimage
from scipy import stats

import celery
from lib.fishface_celery import celery_app
from lib.misc_utilities import image_string_to_array
from lib.fishface_image import FFImage, ff_operation, ff_annotation
from lib.fishface_logging import logger

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


@celery.shared_task(bind=True, name='drone.debug_task')
def debug_task(self, *args, **kwargs):
    return '''
    Request: {0!r}
    Args: {1}
    KWArgs: {2}
    '''.format(self.request, args, kwargs)


def image_from_file(file_path):
    return FFImage(cv2.imread(file_path, 0))


@ff_operation
def delta_image(image, cal_image, ff_image=None):
    if 'FFImage' in str(cal_image.__class__):
        cal_image = cal_image.array

    # adjustment for overall brightness delta
    delta_mode = stats.mstats.mode(image.astype(np.int16) - cal_image.astype(np.int16),
                                   axis=None)
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


def better_delta(data, cal):
    cal_over_data = (256*data / (cal.astype(np.uint16) + 1)).clip(0,255)
    grain_extract_cal_data = (data - cal + 128).clip(0,255)
    dodge_cod_ge = 255 - (cv2.divide((256 * grain_extract_cal_data),
                                     cv2.subtract(255, cal_over_data) + 1)).clip(0,255)

    return dodge_cod_ge.astype(np.uint8)


def min_avg_max(min_val, max_val, ints=True):
    result = [
        min_val,
        (float(min_val) + max_val) / 2,
        max_val,
        ]

    if ints:
        result = map(int, result)

    return result


def mam_envelope(envelope, name, ints=True):
    return min_avg_max(envelope[name + '_min'], envelope[name + '_max'], ints=ints)


@celery.shared_task(name='drone.get_fish_contour')
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

    image.meta['timestamp'] = time.time()

    return image.meta


@celery.shared_task(name='drone.classify_data')
def classify_data(data, estimator, scaler):
    scaled_data = scaler.transform(data)
    return zip(data, estimator.predict(scaled_data))


@celery.shared_task(name='drone.compute_automatic_tags_with_estimator')
def compute_automatic_tags_with_estimator(analyses, estimator, scaler, label_deltas):
    automatic_tags = list()
    for id, hu, centroid, orientation in analyses:
        cluster_label = str(estimator.predict(scaler.transform(hu))[0])

        adjustment = label_deltas[cluster_label]

        automatic_tags.append({
            'analysis_id': id,
            'centroid': centroid,
            'orientation': orientation + adjustment,
        })

    return automatic_tags


@celery.shared_task(name='drone.tagged_data_to_ellipse_box')
def tagged_data_to_ellipse_box(args):
    tag_id, data_jpeg, cal_jpeg, start, degrees, radius_of_roi = args

    data = cv2.imdecode(np.fromstring(data_jpeg, np.uint8), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    cal = cv2.imdecode(np.fromstring(cal_jpeg, np.uint8), cv2.CV_LOAD_IMAGE_GRAYSCALE)

    delta = better_delta(data, cal)
    start = np.array(start)

    adjust = np.array([int(radius_of_roi), int(radius_of_roi/2)], dtype=np.int32)

    retval, roi_corner, roi_far_corner = cv2.clipLine(
        (0, 0, 512, 384),
        tuple(start - adjust),
        tuple(start + adjust),
    )

    rotate_matrix = cv2.getRotationMatrix2D(tuple(start), degrees, 1)
    roi = cv2.warpAffine(delta, rotate_matrix, (512, 384))[
        roi_corner[1]:roi_far_corner[1],
        roi_corner[0]:roi_far_corner[0]
    ]
    roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2RGB)

    roi_corner = np.array(roi_corner)
    start = start - roi_corner

    color = int(np.average(
        roi[start[1] - 2:start[1] + 2, start[0] - 2:start[0] + 2].astype(np.float32)
    ))

    scores = list()
    for x in range(20, 60):
        y_min = int(x/2.3)
        y_max = int(x/1.5)
        for y in range(y_min, y_max):
            template = np.zeros((y, x, 3), dtype=np.uint8)
            cv2.ellipse(img=template, box=((x // 2, y // 2), (x, y), 0),
                        color=(color, color, color), thickness=-1)
            match = cv2.minMaxLoc(cv2.matchTemplate(roi, template, cv2.TM_SQDIFF_NORMED))
            scores.append((match[0], (x,y), match[2]))

    good_scores = sorted(scores)[:10]
    best_score, ellipse_size, ellipse_corner = sorted(good_scores, key=lambda x: -x[1][0]*x[1][1])[0]

    return (tag_id, ellipse_size, color)


@celery.shared_task(name='drone.compute_automatic_tags_with_ellipse_search')
def compute_automatic_tags_with_ellipse_search(taggables, cals):
    image_tags = list()
    for (image_id, data_jpeg, cal_name, envelope) in taggables:

        delta = better_delta(image_string_to_array(data_jpeg),
                             image_string_to_array(cals[cal_name]))

        colors = mam_envelope(envelope, 'color')
        majors = mam_envelope(envelope, 'major')
        ratios = mam_envelope(envelope, 'ratio', ints=False)

        results = list()
        for color in colors:
            for angle in range(0, 180, 10):
                for ratio in ratios:
                    for major in majors:
                        template = np.zeros([int(envelope['major_max']) + 2] * 2, dtype=np.uint8)
                        axes = (int(0.5 * major), int(0.5 * major / ratio))
                        ellipse_params = {
                            'img': template,
                            'center': tuple([int(envelope['major_max']//2)] * 2),
                            'axes': axes,
                            'angle': angle,
                            'startAngle': 0,
                            'endAngle': 360,
                            'color': int(color),
                            'thickness': -1,
                        }
                        cv2.ellipse(**ellipse_params)
                        non_zeroes = np.where(template!=0)
                        nz_mins = np.amin(non_zeroes, axis=1)
                        nz_maxes = np.amax(non_zeroes, axis=1)
                        template = template[nz_mins[0]:nz_maxes[0] + 1, nz_mins[1]:nz_maxes[1] + 1]
                        match = cv2.minMaxLoc(cv2.matchTemplate(
                            delta, template, cv2.TM_SQDIFF_NORMED))
                        results.append((match[0], (color, angle, ratio, major),
                                        (match[2][0] + axes[1], match[2][1] + axes[0])
                                       ))

        intermediate_result = min(results)
        (color, angle_approx, ratio, major) = intermediate_result[1]
        axes = (int(major/2), int(0.5*major/ratio))

        # for the second part of the algorithm, prefer a bit fatter ellipse
        ratio -= - 0.2

        results = list()
        for angle in range(angle_approx - 11, angle_approx + 12):
            template = np.zeros([major+2] * 2, dtype=np.uint8)
            ellipse_params = {
                'img': template,
                'center': tuple([int(envelope['major_max']//2)] * 2),
                'axes': axes,
                'angle': angle,
                'startAngle': 0,
                'endAngle': 360,
                'color': color,
                'thickness': -1,
            }
            cv2.ellipse(**ellipse_params)
            non_zeroes = np.where(template!=0)
            nz_mins = np.amin(non_zeroes, axis=1)
            nz_maxes = np.amax(non_zeroes, axis=1)
            template = template[nz_mins[0]:nz_maxes[0]+1, nz_mins[1]:nz_maxes[1]+1]
            match = cv2.minMaxLoc(cv2.matchTemplate(delta, template, cv2.TM_SQDIFF_NORMED))
            results.append((
                match[0],
                angle,
                (match[2][0] + axes[1], match[2][1] + axes[0])
            ))

        result = min(results)
        score, angle, center = result

        mask = np.ones((15, 15), dtype=np.uint8) * color

        tail_search_radius = 0.75 * major

        tail_center = tuple(map(int,
                                (center[0] - tail_search_radius * math.cos(math.radians(angle)),
                                 center[1] - tail_search_radius * math.sin(math.radians(angle)))))
        tail_candidate = delta[tail_center[1] - 7:tail_center[1] + 8,
                               tail_center[0] - 7:tail_center[0] + 8]

        angle2 = (angle + 180) % 360
        tail_center2 = tuple(map(int,
                                 (center[0] - tail_search_radius * math.cos(math.radians(angle2)),
                                  center[1] - tail_search_radius * math.sin(math.radians(angle2)))))
        tail_candidate2 = delta[tail_center2[1] - 7:tail_center2[1] + 8,
                                tail_center2[0] - 7:tail_center2[0] + 8]

        diff = np.sum(cv2.absdiff(mask, tail_candidate) ** 2)
        diff2 = np.sum(cv2.absdiff(mask, tail_candidate2) ** 2)

        if diff2 < diff:
            angle = angle2

        length = major / 2

        sin_a = math.sin(math.radians(angle))
        cos_a = math.cos(math.radians(angle))

        start = tuple(map(int, (center[0] - length * 0.25 * cos_a,
                                center[1] - length * 0.25 * sin_a)))
        end = tuple(map(int, (center[0] - length * cos_a,
                              center[1] - length * sin_a)))

        image_tags.append({
            'image_id': image_id,
            'start': start,
            'end': end,
            'score': score
        })

    return image_tags


class ImageProcessingException(Exception):
    pass