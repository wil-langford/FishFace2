#!/bin/env python
import os
import sys
import multiprocessing
import json
import math

import cv2
import numpy as np

import lib.cluster_utilities as lcu
from lib.workers.drone_tasks import mam_envelope, better_delta
import etc.cluster_config as cl_conf

#SBATCH --job-name=ellipse_search
#SBATCH --output=/home/wsl/var/log/cluster/ellipse_search_%j.out
#SBATCH --time=15:00
#SBATCH --nodes=1
#SBATCH --exclusive

if len(sys.argv) > 1:
    job_spec_filename = sys.argv[1]
    job_id = os.environ['SLURM_JOB_ID']
    result_filename = job_spec_filename + '.result'
    result_partial_filename = result_filename + '.part'
    jid_filename = job_spec_filename + '.jid'

    with open(jid_filename, 'wt') as jid_file:
        jid_file.write(job_id)

    with open(job_spec_filename, 'rt') as job_spec_file:
        job_list_json = job_spec_file.read()

    job_list = json.loads(job_list_json)
else:
    print 'You need to specify a job_spec_filename on the command line as the sole argument.'
    sys.exit()

# get number of cores available to job
ncores = cl_conf.SLURM_COMPUTE_NODE_CORES

if not ncores:
    try:
        ncores = int(os.environ["SLURM_JOB_CPUS_PER_NODE"])
    except KeyError:
        ncores = multiprocessing.cpu_count()

# create pool of worker processess
p = multiprocessing.Pool(ncores)


def find_ellipse_and_return_tag(args):
    (image_id, remote_data_filename, remote_cal_filename, envelope) = args

    data_filename = lcu.remote_to_local_filename(remote_data_filename)
    cal_filename = lcu.remote_to_local_filename(remote_cal_filename)

    delta = better_delta(
        cv2.imread(data_filename, 0),
        cv2.imread(cal_filename, 0)
    )

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
                        'center': tuple([int(envelope['major_max'] // 2)] * 2),
                        'axes': axes,
                        'angle': angle,
                        'startAngle': 0,
                        'endAngle': 360,
                        'color': int(color),
                        'thickness': -1,
                    }
                    cv2.ellipse(**ellipse_params)
                    non_zeroes = np.where(template != 0)
                    nz_mins = np.amin(non_zeroes, axis=1)
                    nz_maxes = np.amax(non_zeroes, axis=1)
                    template = template[nz_mins[0]:nz_maxes[0] + 1, nz_mins[1]:nz_maxes[1] + 1]
                    match = cv2.minMaxLoc(cv2.matchTemplate(
                        delta, template, cv2.TM_SQDIFF_NORMED))
                    results.append((
                        match[0], (color, angle, ratio, major),
                        (match[2][0] + axes[1], match[2][1] + axes[0])
                    ))

    intermediate_result = min(results)
    (color, angle_approx, ratio, major) = intermediate_result[1]
    axes = (int(major / 2), int(0.5 * major / ratio))

    # for the second part of the algorithm, prefer a bit fatter ellipse
    ratio -= - 0.2

    results = list()
    for angle in range(angle_approx - 11, angle_approx + 12):
        template = np.zeros([major + 2] * 2, dtype=np.uint8)
        ellipse_params = {
            'img': template,
            'center': tuple([int(envelope['major_max'] // 2)] * 2),
            'axes': axes,
            'angle': angle,
            'startAngle': 0,
            'endAngle': 360,
            'color': color,
            'thickness': -1,
        }
        cv2.ellipse(**ellipse_params)
        non_zeroes = np.where(template != 0)
        nz_mins = np.amin(non_zeroes, axis=1)
        nz_maxes = np.amax(non_zeroes, axis=1)
        template = template[nz_mins[0]:nz_maxes[0] + 1, nz_mins[1]:nz_maxes[1] + 1]
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

    tag = {
        'image_id': image_id,
        'start': start,
        'end': end,
        'score': score
    }

    return tag


try:
    # apply work function in parallel
    tags = p.map(find_ellipse_and_return_tag, job_list)

    # write file and make sure it's completely written
    with open(result_partial_filename, 'wt') as result_file:
        result_file.write(json.dumps(tags))
        result_file.flush()
        os.fsync(result_file.fileno())

    # rename the file so that the result collector will pick it up
    os.rename(result_partial_filename, result_filename)
    os.remove(job_spec_filename)
    os.remove(jid_filename)

    sys.exit(0)
except:
    with open(job_spec_filename + '.error') as error_file:
        error_file.write(job_list_json)
    sys.exit(1)