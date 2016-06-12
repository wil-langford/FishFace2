import math
import time
import datetime

import cv2
import numpy as np

import merrellyze_pb2
from google.appengine.api import taskqueue


def _better_delta(data, cal):
    cal_over_data = (256*data / (cal.astype(np.uint16) + 1)).clip(0, 255)
    grain_extract_cal_data = (data - cal + 128).clip(0, 255)
    dodge_cod_ge = 255 - (cv2.divide((256 * grain_extract_cal_data),
                                     cv2.subtract(255, cal_over_data) + 1)).clip(0, 255)

    return dodge_cod_ge.astype(np.uint8)


def _stepper(params):
    return [params['min'] + i*(params['max']-params['min'])/float(params['steps']-1)
            for i in range(params['steps'])]


class MerrellyzeDroneServer():
    def __init__(self):
        self.equeue = taskqueue.Queue(name='ellipse_search')
        self.rqueue = taskqueue.Queue(name='fresh_results')

        self._keep_running = True
        self._started_waiting_at = None

    def _am_i_done(self):
        if self._started_waiting_at - datetime.datetime.now() > 300:
            self._keep_running = False

    def run(self):
        while self._keep_running:
            tasks = ''
            self._started_waiting_at = datetime.datetime.now()

            while len(tasks)==0 and self._keep_running:
                tasks = self.equeue.lease_tasks(100,10)
                time.sleep(10)
                self._am_i_done()

            task_successes = list()

            for task in tasks:
                if self.find_ellipse(task):
                    task_successes.append(task)

            self.equeue.delete_tasks(task_successes)


    def find_ellipse(self, task):
        revision = 1
        tagging_method = "find_ellipse"

        # TODO: break out the image from the task
        image = merrellyze_pb2.Image.ParseFromString('image_as_string')

        data_path = image.path
        cal_path = image.cal.path

        delta = _better_delta(
            cv2.imread(data_path, 0),
            cv2.imread(cal_path, 0)
        )

        envelope = {
            'color': {
                'min': 20,
                'max': 40,
                'steps': 3,
            },
            'major': {
                'min': 20,
                'max': 60,
                'steps': 3,
            },
            'ratio': {
                'min': 1.5,
                'max': 2.3,
                'steps': 3,
            },
        }

        results = list()
        for color in _stepper(envelope['color']):
            for angle in range(0, 180, 10):
                for ratio in _stepper(envelope['ratio']):
                    for major in _stepper(envelope['major']):
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

        start = merrellyze_pb2.Location()
        end = merrellyze_pb2.Location()

        start.x, start.y = tuple(map(int, (center[0] - length * 0.25 * cos_a,
                                           center[1] - length * 0.25 * sin_a)))
        end.x, end.y = tuple(map(int, (center[0] - length * cos_a,
                                       center[1] - length * sin_a)))

        tag = merrellyze_pb2.EllipseTag()
        tag.image_id = image.id
        tag.start = start
        tag.end = end
        tag.score = score
        tag.tagging_method = tagging_method
        tag.revision = revision
        tag.request_tag = image.request_id

        response = merrellyze_pb2.ResultResponse()
        response.tags.add(tag)

        self.rqueue.add(merrellyze_pb2.ResultResponse.SerializeToString(response))

        return True