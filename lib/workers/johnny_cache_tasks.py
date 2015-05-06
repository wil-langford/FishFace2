import os
import multiprocessing
from contextlib import closing

import fabric.network as fn
from fabric.state import env as fabric_env

import celery
from lib.misc_utilities import n_chunkify, remote_to_local_filename

import etc.cluster_config as cl_conf

#
# Convenience functions
#


def fetch_files(file_list):
    fetch_successes = list()
    fetch_file_list = list()

    # determine what's already here
    for remote_filename in file_list:
        local_filename = remote_to_local_filename(remote_filename)
        if os.path.isfile(local_filename):
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
                            l_file.write(r_file.read())


@celery.shared_task(name='johnny_cache.cache_files')
def cache_files(file_list, extra, parallel_processes=4):
    pool = multiprocessing.Pool(parallel_processes)
    successes = pool.map(fetch_files, n_chunkify(parallel_processes, file_list))

    success = all(map(all, successes)) and sum(map(len, successes)) == len(file_list)
    return success, extra