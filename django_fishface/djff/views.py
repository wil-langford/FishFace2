import logging
import numpy as np
import datetime
import time
import threading

import requests

import django.shortcuts as ds
import django.http as dh
import django.utils as du
import django.core.urlresolvers as dcu
import django.core.files.storage as dcfs
import django.views.decorators.csrf as csrf_dec
import django.utils.timezone as dut
import django.views.generic as dvg
import django.views.generic.edit as dvge

import cv2

from djff.models import (
    Experiment,
    Image,
    Species,
    CaptureJobTemplate,
    CaptureJobRecord,
)


IMAGERY_SERVER_IP = 'raspi'
IMAGERY_SERVER_PORT = 18765

IMAGERY_SERVER_URL = 'http://{}:{}/'.format(
    IMAGERY_SERVER_IP,
    IMAGERY_SERVER_PORT
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filename='/tmp/djangoLog.log',)

logger = logging.getLogger(__name__)


def _image_response_from_numpy_array(img, extension):
    """
    Returns an HttpResponse with an image mimetype based on the
    extension given.

    :param img: The numpy array to serve as an image.
    :param extension: "jpg" and "png" work.  Others can be tried at
                      your own risk.
    """
    out = cv2.imencode(".{}".format(extension), img)[1].tostring()
    response = dh.HttpResponse(out, content_type="image/{}".format(
        extension
    ))
    return response


def _file_object_to_numpy_array(image_file):
    img_raw = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    return cv2.imdecode(img_raw, 0)


def _file_path_to_numpy_array(image_file_path):
    with dcfs.default_storage.open(
            image_file_path,
            mode='r'
    ) as image_file:
        return _file_object_to_numpy_array(image_file)


#######################
###  General Views  ###
#######################


def index(request):
    return dh.HttpResponseRedirect(dcu.reverse('djff:xp_index'))


@csrf_dec.csrf_exempt
def receive_telemetry(request):

    payload = request.POST

    if payload['command'] == 'job_status_update':
        cjr = ds.get_object_or_404(CaptureJobRecord,
                                   pk=int(payload['cjr_id']))

        if payload['status'] == 'running':
            cjr.running = True
        else:
            cjr.running = False

        cjr.job_start = du.timezone.datetime.utcfromtimestamp(
            float(payload['job_start_timestamp'])
        ).replace(tzinfo=dut.utc)

        cjr.total = int(payload['total'])
        cjr.remaining = int(payload['remaining'])

        if payload['job_end_timestamp']:
            cjr.job_stop = du.timezone.datetime.utcfromtimestamp(
                float(payload['job_end_timestamp'])
            ).replace(tzinfo=dut.utc)

        cjr.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:xp_index'))


##########################
###  Experiment views  ###
##########################


def xp_index(request):
    xp_list = Experiment.objects.all().order_by(
        'xp_start'
    )
    context = {'xp_list': xp_list}
    return ds.render(request, 'djff/xp_index.html', context)


def xp_new(request):
    xp = Experiment()
    xp.xp_start = du.timezone.now()
    xp.name = "New experiment"
    try:
        xp.species = Species.objects.all()[0]
    except IndexError:
        default_species = Species()
        default_species.name = "hypostomus plecostomus"
        default_species.shortname = "HP"
        default_species.save()
        xp.species = default_species
    xp.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_rename',
                    args=(xp.id,))
    )


def xp_rename(request, xp_id):
    xp = ds.get_object_or_404(Experiment, pk=xp_id)
    return ds.render(
        request,
        'djff/xp_rename.html',
        {'xp': xp}
    )


def xp_renamer(request, xp_id):
    xp = ds.get_object_or_404(Experiment, pk=xp_id)

    xp.name = request.POST['new_name']
    xp.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_capture', args=(xp.id,))
    )


def xp_capturer(request):
    xp = ds.get_object_or_404(Experiment, pk=int(request.POST['xp_id']))

    payload = {
        'command': 'post_image',
        'xp_id': xp.id,
        'current': request.POST['current'],
        'voltage': request.POST['voltage'],
        'species': xp.species.shortname
    }

    # default value for is_cal_image
    payload['is_cal_image'] = request.POST.get(
        'is_cal_image',
        False
    )

    # default value for cjr_id
    payload['cjr_id'] = request.POST.get(
        'cjr_id',
        0
    )

    # if it's not a cal image OR if it's a cal image and the user
    # checked the "ready to capture cal image" box...
    if (not request.POST['is_cal_image'] == 'True' or
            request.POST.get('cal_ready', '') == 'True'):
        r = requests.get(IMAGERY_SERVER_URL, params=payload)

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_capture',
                    args=(payload['xp_id'],))
    )


def xp_capture(request, xp_id):
    try:
        xp = ds.get_object_or_404(Experiment, pk=xp_id)
    except ds.Http404:
        return dh.HttpResponseRedirect(
            dcu.reverse(
                'djff:xp_new',
                args=tuple(),
            )
        )

    xp_images = Image.objects.filter(
        xp__id=xp_id
    )

    cal_images = xp_images.filter(
        is_cal_image=True
    )

    data_images = xp_images.filter(
        is_cal_image=False
    )

    cjts = CaptureJobTemplate.objects.all()

    running_jobs = CaptureJobRecord.objects.filter(
        running=True
    )

    cjrs = CaptureJobRecord.objects.filter(xp__id=xp.id)

    images_by_cjr = [
        (cjr_obj, Image.objects.filter(cjr__id=cjr_obj.id))
        for cjr_obj in
        cjrs
    ]

    return ds.render(
        request,
        'djff/xp_detail.html',
        {
            'xp': xp,
            'xp_images': xp_images,
            'cal_images': cal_images,
            'data_images': data_images,
            'running_jobs': running_jobs,
            'cjts': cjts,
            'images_by_cjr': images_by_cjr,
        }
    )


#######################
###  Species views  ###
#######################


class SpeciesIndex(dvg.ListView):
    context_object_name = 'context'
    template_name = 'djff/sp_index.html'
    model = Species


class SpeciesUpdate(dvge.UpdateView):
    model = Species
    context_object_name = 'context'
    template_name = 'djff/sp_detail.html'
    success_url = dcu.reverse_lazy('djff:sp_index')


class SpeciesDelete(dvge.DeleteView):
    model = Species
    context_object_name = 'context'
    success_url = dcu.reverse_lazy('djff:sp_index')


def sp_new(request):
    sp = Species()
    sp.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:sp_detail',
                    args=(sp.id,))
    )


##################################
###  CaptureJobTemplate views  ###
##################################


class CaptureJobTemplateIndex(dvg.ListView):
    context_object_name = 'context'
    template_name = 'djff/cjt_index.html'
    model = CaptureJobTemplate


class CaptureJobTemplateUpdate(dvge.UpdateView):
    model = CaptureJobTemplate
    context_object_name = 'context'
    template_name = 'djff/cjt_detail.html'
    success_url = dcu.reverse_lazy('djff:cjt_index')


class CaptureJobTemplateDelete(dvge.DeleteView):
    model = CaptureJobTemplate
    context_object_name = 'context'
    success_url = dcu.reverse_lazy('djff:cjt_index')


def cjt_new(request):
    cjt = CaptureJobTemplate()
    cjt.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:cjt_detail',
                    args=(cjt.id,))
    )


def run_capturejob(request, xp_id, cjt_id):
    cjt = ds.get_object_or_404(CaptureJobTemplate, pk=cjt_id)
    xp = ds.get_object_or_404(Experiment, pk=xp_id)
    cjr = CaptureJobRecord(
        xp=xp,
        voltage=cjt.voltage,
        current=cjt.current,
        running=True,
    )
    cjr.save()

    payload = {
        'command': 'set_psu',
        'xp_id': xp.id,
        'species': xp.species.shortname,
        'cjr_id': cjr.id,
        'voltage': cjr.voltage,
        'current': cjr.current,
        'duration': cjt.duration,
        'interval': cjt.interval,
        'startup_delay': cjt.startup_delay,
        'enable_output': int(True),
    }

    logger.info(str(payload))

    def job_thread(inner_payload):
        time.sleep(cjt.startup_delay)

        requests.get(IMAGERY_SERVER_URL, params=inner_payload)

        inner_payload['command'] = 'run_capturejob'

        requests.get(IMAGERY_SERVER_URL, params=inner_payload)

        inner_payload['command'] = 'set_psu'
        inner_payload['enable_output'] = int(False)

        requests.get(IMAGERY_SERVER_URL, params=inner_payload)

    thread = threading.Thread(
        target=job_thread,
        args=(payload,)
    )
    thread.start()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_capture',
                    args=(payload['xp_id'],))
    )


################################
###  Internal Capture views  ###
################################


@csrf_dec.csrf_exempt
def image_capturer(request):
    logger.info("processing request")
    if request.method == 'POST':
        logger.debug(request.POST)

        logger.info("command: {}".format(request.POST['command']))

        if request.POST['command'] == 'post_image':
            xp = ds.get_object_or_404(
                Experiment,
                pk=request.POST['xp_id']
            )

            logger.info("Experiment: {} (ID {})".format(
                xp.name,
                xp.id
            ))

            is_cal_image = (str(request.POST['is_cal_image']).lower()
                            in ['true', 't', 'yes', 'y', '1'])
            voltage = float(request.POST['voltage'])
            current = float(request.POST['current'])

            capture_timestamp = datetime.datetime.utcfromtimestamp(
                float(request.POST['capture_time'])
            ).replace(tzinfo=dut.utc)

            try:
                cjr = ds.get_object_or_404(
                    CaptureJobRecord,
                    pk=int(request.POST['cjr_id'])
                )
            except dh.Http404:
                cjr = None

            logger.info("storing image")

            captured_image = Image(
                xp=xp,
                capture_timestamp=capture_timestamp,
                voltage=voltage,
                is_cal_image=is_cal_image,
                cjr=cjr,
                image_file=request.FILES[
                    request.POST['filename']
                ],
            )
            captured_image.save()

            logger.info("image stored with ID {}".format(
                captured_image.id
            ))

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_index'),
    )
