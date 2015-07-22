#!/bin/env python

#SBATCH --job-name=envelope_update
#SBATCH --output=/home/wsl/var/log/cluster/envelope_update_%j.out
#SBATCH --time=15:00
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --partition=main,main2

import os
import sys
import multiprocessing
import json

import cv2
import numpy as np

import lib.cluster_utilities as lcu
import etc.cluster_config as cl_conf


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


def tagged_data_to_ellipse_envelope(job_spec):
    tag_id, remote_data_filename, remote_cal_filename, start, degrees, radius_of_roi = job_spec

    with open(lcu.remote_to_local_filename(remote_data_filename), 'rb') as data_file:
        data_jpeg = data_file.read()

    with open(lcu.remote_to_local_filename(remote_cal_filename), 'rb') as cal_file:
        cal_jpeg = cal_file.read()

    data = cv2.imdecode(np.fromstring(data_jpeg, np.uint8), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    cal = cv2.imdecode(np.fromstring(cal_jpeg, np.uint8), cv2.CV_LOAD_IMAGE_GRAYSCALE)

    delta = lcu.better_delta(data, cal)
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


try:
    # create pool of worker processess
    pool = multiprocessing.Pool(ncores)

    # apply work function in parallel
    tags = pool.map(tagged_data_to_ellipse_envelope, job_list)

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
except Exception as exc:
    with open(job_spec_filename + '.error', 'wt') as error_file:
        error_file.write(job_list_json)
        error_file.write('\n\nEXCEPTION:\n\n')
        error_file.write(exc)
    sys.exit(1)