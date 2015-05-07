import os
import tempfile
import json
import subprocess

import celery
from lib.fishface_celery import celery_app

import etc.cluster_config as cl_conf
import etc.fishface_config as ff_conf

@celery.shared_task(name='cluster_dispatch.ping')
def ping():
    return True


@celery.shared_task(name='cluster_dispatch.ellipse_search')
def ellipse_search(args):
    success, taggables = args
    if not success:
        return False

    with tempfile.NamedTemporaryFile(mode='wt', delete=False, dir=cl_conf.JOB_FILE_DIR,
                                     prefix='ellipse_search_job_', ) as job_file:
        job_filename = job_file.name
        job_file.write(json.dumps(taggables))
        job_file.flush()
        os.fsync(job_file.fileno())

    subprocess.call(['sbatch',
                     os.path.join(ff_conf.BIN, 'cluster', 'sbatch_ellipse_search.py'),
                     job_filename])

    return True


@celery.shared_task(name='cluster_dispatch.tagged_data_to_ellipse_envelope')
def tagged_data_to_ellipse_envelope(args):
    success, jobs = args
    if not success:
        return False

    with tempfile.NamedTemporaryFile(mode='wt', delete=False, dir=cl_conf.JOB_FILE_DIR,
                                     prefix='tagged_data_to_ellipse_envelope_job_',) as job_file:
        job_filename = job_file.name
        job_file.write(json.dumps(jobs))
        job_file.flush()
        os.fsync(job_file.fileno())

    subprocess.call(['sbatch',
                     os.path.join(ff_conf.BIN, 'cluster',
                                  'sbatch_tagged_data_to_ellipse_envelope.py'),
                     job_filename])

    return True