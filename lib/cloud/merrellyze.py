import datetime
import merrellyze_pb2
from google.appengine.api import taskqueue


class EllipseSearchServer(merrellyze_pb2.BetaEllipseSearcherServicer):
    def __init__(self):
        self.queue = taskqueue.Queue(name='ellipse_search')

    @staticmethod
    def _taskify(image, cal):
        image.cal = cal
        return merrellyze_pb2.Image.SerializeToString(image)

    def EllipseSearch(self, request, context):
        ## tagging is a beta feature and the documentation is a bit sparse.
        ## however, I'm already pretty sure that I'll want to use the DTG of the
        ## request RPC as the tag to group tasks.
        # tag = datetime.datetime.now().isoformat()

        response = merrellyze_pb2.EllipseSearchResponse()

        for cjr in request.cjrs:
            try:
                cal = cjr.cal_image
                self.queue.add(taskqueue.Task(method='PULL',
                                              payload=self._taskify(image, cal))
                               for image in cjr.images)
                cjr_only_id = merrellyze_pb2.CaptureJobRecord()
                cjr_only_id = cjr.id
                response.cjrs_in_progress.add(cjr_only_id)
            except MerrellyzeError as e:
                error_response = merrellyze_pb2.ErrorCJREllipseSearch
                error_response.id = cjr.id
                error_response.message = e.message
                response.cjrs_with_errors.add(cjr)


class ResultFetchServer(merrellyze_pb2.BetaResultFetcherServicer):
    def __init__(self):
        self.queue = taskqueue.Queue(name='fresh_results')


    def ResultFetch(self, request, context):
        if len(request.cjrs):
            for cjr in request.cjrs:
                cal = cjr.cal_image
                self.queue.add(taskqueue.Task(method='PULL',
                                              payload=self._taskify(image, cal))
                               for image in cjr.images)
        else:
            self.queue.lease_tasks(300, 500, deadline=10)



class MerrellyzeError(Exception): pass