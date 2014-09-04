#!/usr/bin/env python

"""
This module is a small program intended to run on a Raspberry Pi with
attached camera module and send imagery to a FishFace server.
"""

import picamera
import threading
import time
import io
import BaseHTTPServer
import urlparse
import requests
import datetime
import instruments as ik

HOST = ''
PORT = 18765

IMAGE_POST_URL = "http://localhost:8100/fishface/upload_imagery/"
TELEMETRY_URL = "http://localhost:8100/fishface/telemetry/"

DATE_FORMAT = "%Y-%m-%d-%H:%M:%S"


def delay_until(unix_timestamp):
    now = time.time()
    while now < unix_timestamp:
        time.sleep(unix_timestamp-now)
        now = time.time()


class ImageryServer(object):
    """
    """

    def __init__(self):
        self._keep_capturing = True
        self._keep_capturejob_looping = True

        self.camera = picamera.PiCamera()
        self.camera.resolution = (2048, 1536)
        self.camera.rotation = 180

        self._job_status = None

        self._current_frame_capture_time = None

        self.power_supply = ik.hp.HP6652a.open_serial('/dev/ttyUSB0',
                                                      57600)

        self._current_frame = None

    def _capture_new_current_frame(self):
        stream = io.BytesIO()

        new_frame_capture_time = time.time()
        self.camera.capture(
            stream,
            format='jpeg'
        )

        image = stream.getvalue()

        self._current_frame_capture_time = new_frame_capture_time
        self._current_frame = image

    def get_current_frame(self):
        return self._current_frame

    def awb_mode(self, mode=None):
        if mode is None:
            return self.camera.awb_mode

        if mode in ['off', 'auto']:
            self.camera.awb_mode = mode
        else:
            raise Exception("Invalid AWB mode for raspi camera: " +
                            "{}".format(mode))

    def brightness(self, br=None):
        if br is None:
            return self.camera.brightness

        if 0 <= br <= 100:
            self.camera.brightness = br
        else:
            raise Exception("Invalid brightness setting for raspi " +
                            "camera: {}".format(br))

    def run(self):
        def image_capture_loop():
            while self._keep_capturing:
                self._capture_new_current_frame()
            self.camera.close()

        thread = threading.Thread(target=image_capture_loop)
        print "starting thread"
        thread.start()

        print "thread started"

        server_address = (HOST, PORT)
        httpd = BaseHTTPServer.HTTPServer(
            server_address,
            CommandHandler
        )
        httpd.parent = self

        print "about to start http server"

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self._keep_capturing = False
            self._keep_capturejob_looping = False
            httpd.server_close()

    def post_current_image_to_server(self, metadata, sync=True):
        current_frame = self._current_frame
        current_frame_capture_time = self._current_frame_capture_time

        stream = io.BytesIO(current_frame)

        image_dtg = datetime.datetime.fromtimestamp(
            current_frame_capture_time
        ).strftime(
            DATE_FORMAT
        )

        since_epoch = time.time()

        image_filename = '{}_{}.jpg'.format(
            image_dtg,
            since_epoch
        )

        print 'posting {}'.format(image_filename)

        is_cal_image = (str(metadata['is_cal_image']).lower()
                        in ['true', 't', 'yes', 'y', '1'])

        metadata['filename'] = image_filename
        metadata['capture_time'] = current_frame_capture_time
        metadata['is_cal_image'] = str(is_cal_image)

        files = {image_filename: stream}

        t = time.time()

        if sync:
            r = requests.post(
                IMAGE_POST_URL,
                files=files,
                data=metadata
            )
            print time.time() - t
            return r
        else:
            def async_image_post(url, files_to_post, metadata_to_post):
                return requests.post(
                    url,
                    files=files_to_post,
                    data=metadata_to_post
                )

            async_thread = threading.Thread(
                target=async_image_post,
                args=(IMAGE_POST_URL, files, metadata)
            )
            async_thread.start()
            return

    def receive_telemetry(self, raw_payload):
        payload = dict([field.split('=')
                        for field in raw_payload.split('&')])

        result = "no result"

        if payload['command'] == 'post_image':
            result = self.post_current_image_to_server(payload)

        if payload['command'] == 'run_capturejob':
            result = self.run_capturejob(payload)

        if payload['command'] == 'job_status':
            result = self.post_job_status_update(payload)

        if result and result.status_code == 500:
            result = result.text

        return result

    def send_telemetry(self, payload, files=None):
        return requests.post(
            TELEMETRY_URL,
            data=payload,
            files=files,
        )

    def post_job_status_update(self):
        if self._job_status is None:
            result = self.send_telemetry(
                {
                    'command': 'job_status_update',
                    'status': 'no_job_running',
                }
            )
        else:
            payload = self._job_status.copy()
            payload['command'] = 'job_status_update'

            result = self.send_telemetry(payload)

        return result

    def run_capturejob(self, payload):
        self._job_status = {
            'cjr_id': payload['cjr_id'],
            'status': 'running',
            'job_start_timestamp': time.time(),
            'job_end_timestamp': ''
        }

        duration = float(payload['duration'])
        interval = float(payload['interval'])
        startup_delay = float(payload['startup_delay'])

        first_capture_at = time.time() + startup_delay

        capture_times = [first_capture_at]
        for i in range(1, int(duration / interval) + 1):
            capture_times.append(first_capture_at + i*interval)

        self._keep_capturejob_looping = True

        metadata = {
            'command': 'post_image',
            'is_cal_image': False,
            'voltage': payload['voltage'],
            'xp_id': payload['xp_id'],
            'cjr_id': payload['cjr_id'],
        }

        def capturejob_loop(
                metadata_dict,
                capture_times_list):
            self._job_status['total'] = len(capture_times_list) + 1
            self._job_status['remaining'] = len(capture_times_list) + 1

            total = self._job_status['total']

            for i, next_capture_time in enumerate(capture_times_list):
                if not self._keep_capturejob_looping:
                    break

                delay_until(next_capture_time)
                self.post_current_image_to_server(
                    metadata_dict,
                    sync=False,
                )

                self._job_status['remaining'] = total - i

                self.post_job_status_update()

            self._job_status['job_end_timestamp'] = time.time()

            self._job_status['command'] = 'job_status_update'
            self._job_status['status'] = 'complete'

            self.send_telemetry(
                self._job_status
            )

            self._job_status = None

        thread = threading.Thread(
            target=capturejob_loop,
            args=(metadata, capture_times)
        )
        print (
            ("sending images for capturejob {} for" +
                "experiment {}").format(
                    payload['cjr_id'],
                    payload['xp_id'],
                )
        )
        thread.start()
        print "capturejob thread started"

        # TODO: this could make more sense, but I'm not sure how.  yet.

        return False


class CommandHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)

        # self.send_response(200)
        # self.send_header("Contest-type", "type/html")
        # self.end_headers()

        result = self.server.parent.receive_telemetry(
            parsed_path.query
        )
        self.wfile.write(str(result))


def main():
    imagery_server = ImageryServer()

    imagery_server.run()

    print "exiting"


if __name__ == '__main__':
    main()