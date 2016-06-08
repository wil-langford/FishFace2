import datetime
import merrellyze_pb2
from google.appengine.api import taskqueue


class EllipseSearchServer(merrellyze_pb2.BetaEllipseSearcherServicer):
    def __init__(self):
        pass

    @staticmethod
    def _taskify(image, cal):
        image.cal = cal
        return merrellyze_pb2.Image.SerializeToString(image)

    def EllipseSearch(self, request, context):
        ## tagging is a beta feature and the documentation is a bit sparse.
        ## however, I'm already pretty sure that I'll want to use the DTG of the
        ## request RPC as the tag to group tasks.
        # tag = datetime.datetime.now().isoformat()

        queue = taskqueue.Queue(name='ellipse_search')

        for cjr in request.cjrs:
            cal = cjr.cal_image
            queue.add(taskqueue.Task(method='PULL',
                                     payload=self._taskify(image, cal))
                      for image in cjr.images)


class ResultFetchServer(merrellyze_pb2.BetaResultFetcherServicer):
    pass