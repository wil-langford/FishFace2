import os
import etc.cluster_config as cl_conf
import cv2
import numpy as np


def remote_to_local_filename(remote_filename, local_media_parent=None):
    if local_media_parent is None:
        local_media_parent = cl_conf.LOCAL_CACHE_DIR
    return os.path.join(
        local_media_parent,
        remote_filename[remote_filename.find('media'):]
    )


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


def image_read(path_name, flags=0):
    if not os.path.isfile(path_name):
        raise Exception("File to read is not a file or is not found.")

    return_value = cv2.imread(path_name, flags=flags)

    if return_value is None:
        raise Exception("cv2.imread returned a None value.")

    return return_value


def better_delta(data, cal):
    if data is None:
        raise Exception("Data image is None when calling better_delta.")
    if cal is None:
        raise Exception("Cal image is None when calling better_delta.")
    cal_over_data = (256 * data / (cal.astype(np.uint16) + 1)).clip(0,255)
    grain_extract_cal_data = (data - cal + 128).clip(0,255)
    dodge_cod_ge = 255 - (cv2.divide((256 * grain_extract_cal_data),
                                     cv2.subtract(255, cal_over_data) + 1)).clip(0,255)

    return dodge_cod_ge.astype(np.uint8)