#!/bin/env python
import os
import time
import threading
import json

from lib.fishface_celery import celery_app

from lib.misc_utilities import delay_for_seconds

import etc.cluster_config as cl_conf

relay_to = {
    'ellipse_search': 'results.store_ellipse_search_tags',
    'tagged_data_to_ellipse_envelope': 'results.update_multiple_envelopes',
}

def relay_result_file(file_path):
    print "Relaying results found in filename: {}".format(file_path)

    with open(file_path, 'rt') as result_file:
        result = json.loads(result_file.read())

    job_type = file_path.split('_job_')[0]

    celery_app.send_task(relay_to[job_type],
                         args=(result,))

    os.rename(file_path, file_path + '.relayed')


class RelayThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(RelayThread, self).__init__(*args, **kwargs)
        self._keep_looping = True

    def run(self):
        while self._keep_looping:
            all_filenames = list()
            for (dirpath, dirnames, filenames) in os.walk(cl_conf.JOB_FILE_DIR):
                all_filenames.extend([filename for filename in filenames
                                  if filename.endswith('.result')])
                break

            if all_filenames:
                print "Processing filenames: {}".format(all_filenames)
                for filename in all_filenames:
                    relay_result_file(os.path.join(cl_conf.JOB_FILE_DIR, filename))
            else:
                delay_for_seconds(5)

    def abort(self):
        self._keep_looping = False

relay_thread = RelayThread()

try:
    relay_thread.start()
except KeyboardInterrupt:
    relay_thread.abort()


class RelayException(Exception): pass