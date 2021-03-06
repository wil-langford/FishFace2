from contextlib import closing

import celery
from lib.fishface_celery import celery_app

from lib.misc_utilities import is_file

import fabric.network as fn
import lib.cluster_utilities as lcu

import etc.cluster_config as cl_conf
from fabric.state import env as fabric_env

from lib.fishface_logging import logger


def fetch_files(file_list):
    fetch_successes = list()
    fetch_file_list = list()

    # determine what's already here
    for remote_filename in file_list:
        local_filename = lcu.remote_to_local_filename(remote_filename)
        if is_file(local_filename):
            fetch_successes.append(True)
        else:
            fetch_file_list.append((remote_filename, local_filename))

    if fetch_file_list:
        fabric_env['key_filename'] = cl_conf.SCP_SECRET_KEYFILE

        # fetch what isn't already here
        with closing(fn.connect(cl_conf.SCP_USER, cl_conf.SCP_HOST, cl_conf.SCP_PORT, None)) as ssh:
            with closing(ssh.open_sftp()) as sftp:
                for remote_filename, local_filename in fetch_file_list:
                    with closing(sftp.open(remote_filename)) as r_file:
                        with open(local_filename, 'wb') as l_file:
                            logger("Fetching file: {} to: {}".format(remote_filename, local_filename))
                            try:
                                l_file.write(r_file.read())
                                fetch_successes.append(True)
                            except IOError:
                                fetch_successes.append(False)

    return fetch_successes


@celery.shared_task(name='johnny_cache.cache_files')
def cache_files(file_list, extra):
    successes = fetch_files(file_list)

    success = all(successes) and len(successes) == len(file_list)

    return success, extra