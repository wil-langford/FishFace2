import logging
import numpy as np
import datetime
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
from djff.models import HopperChain
from utils.hoppers import CLASS_PARAMS
import djff.utils


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
    return dh.HttpResponseRedirect(dcu.reverse('djff:experiment_index'))


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

    return dh.HttpResponseRedirect(dcu.reverse('djff:experiment_index'))


##########################
###  Experiment views  ###
##########################


def experiment_index(request):
    experiment_list = Experiment.objects.all().order_by(
        'experiment_start_dtg'
    )
    context = {'experiment_list': experiment_list}
    return ds.render(request, 'djff/experiment_index.html', context)


def experiment_new(request):
    xp = Experiment()
    xp.experiment_start_dtg = du.timezone.now()
    xp.experiment_name = "New experiment"
    xp.species = Species.objects.all()[0]
    xp.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:experiment_rename',
                    args=(xp.id,))
    )


def experiment_rename(request, xp_id):
    xp = ds.get_object_or_404(Experiment, pk=xp_id)
    return ds.render(
        request,
        'djff/experiment_rename.html',
        {'xp': xp}
    )


def experiment_renamer(request, xp_id):
    xp = ds.get_object_or_404(Experiment, pk=xp_id)

    xp.experiment_name = request.POST['new_name']
    xp.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:experiment_capture',
                                               args=(xp.id,)))


def experiment_capturer(request):
    payload = {
        'command': 'post_image',
        'xp_id': request.POST['xp_id'],
        'voltage': request.POST['voltage'],
    }

    payload['is_cal_image'] = request.POST.get(
        'is_cal_image',
        False
    )

    if (not request.POST['is_cal_image'] == 'True' or
        request.POST.get('cal_ready', '') == 'True'):
        r = requests.get(IMAGERY_SERVER_URL, params=payload)

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:experiment_capture',
                    args=(payload['xp_id'],))
    )


def experiment_capture(request, xp_id):
    try:
        xp = ds.get_object_or_404(Experiment, pk=xp_id)
    except ds.Http404:
        return dh.HttpResponseRedirect(
            dcu.reverse(
                'djff:experiment_new',
                args=tuple(),
            )
        )

    xp_images = Image.objects.filter(
        experiment__id=xp_id
    )

    cal_images = xp_images.filter(
        is_cal_image=True
    )

    data_images = xp_images.filter(
        is_cal_image=False
    )

    capturejob_templates = CaptureJobTemplate.objects.all()

    capturerecords = CaptureJobRecord.objects.filter(
        running=True
    )

    blah = "active capturejobs: {}".format(len(capturerecords))

    return ds.render(
        request,
        'djff/experiment_capture.html',
        {
            'xp': xp,
            'xp_images': xp_images,
            'cal_images': cal_images,
            'data_images': data_images,
            'capturerecords': capturerecords,
            'capturejob_templates': capturejob_templates,
            'blah': blah,
        }
    )


##################################
###  CaptureJobTemplate views  ###
##################################


class CaptureJobTemplateIndex(dvg.ListView):
    context_object_name = 'cjt_context'
    template_name = 'djff/capturejobtemplate_list.html'

    def get_queryset(self):
        return CaptureJobTemplate.objects.all()


class CaptureJobTemplateCreate(dvge.CreateView):
    model = CaptureJobTemplate
    context_object_name = 'cjt_context'
    template_name = 'djff/capturejobtemplate_add.html'


class CaptureJobTemplateUpdate(dvge.UpdateView):
    model = CaptureJobTemplate
    context_object_name = 'cjt_context'
    template_name = 'djff/capturejobtemplate_update.html'
    success_url = dcu.reverse_lazy('djff:cjt_list')


class CaptureJobTemplateDelete(dvge.DeleteView):
    model = CaptureJobTemplate
    context_object_name = 'cjt_context'
    success_url = dcu.reverse_lazy('djff:cjt_list')


def run_capturejob(request, xp_id, cjt_id):
    cjt = ds.get_object_or_404(CaptureJobTemplate, pk=cjt_id)
    xp = ds.get_object_or_404(Experiment, pk=xp_id)
    cjr = CaptureJobRecord(
        xp=xp,
        voltage=cjt.voltage,
    )
    cjr.save()

    payload = {
        'command': 'run_capturejob',
        'xp_id': xp.id,
        'cjr_id': cjr.id,
        'voltage': cjr.voltage,
        'duration': cjt.duration,
        'interval': cjt.interval,
        'startup_delay': cjt.startup_delay,
    }

    logger.info(str(payload))

    r = requests.get(IMAGERY_SERVER_URL, params=payload)

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:experiment_capture',
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

        if request.POST['command'] == 'post_image':
            xp = ds.get_object_or_404(
                Experiment,
                pk=request.POST['xp_id']
            )

            is_cal_image = (str(request.POST['is_cal_image']).lower()
                            in ['true', 't', 'yes', 'y', '1'])
            voltage = float(request.POST['voltage'])

            dtg_capture = datetime.datetime.utcfromtimestamp(
                float(request.POST['capture_time'])
            ).replace(tzinfo=dut.utc)

            cjr = ds.get_object_or_404(
                CaptureJobRecord,
                pk=int(request.POST['cjr_id'])
            )

            captured_image = Image(
                experiment=xp,
                dtg_capture=dtg_capture,
                voltage=voltage,
                is_cal_image=is_cal_image,
                capturejob=cjr,
                image_file=request.FILES[
                    request.POST['filename']
                ],
            )
            captured_image.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:experiment_index'),
    )


###########################
###  HopperChain views  ###
###########################


def hopperchain_index(request):
    hopperchain_list = HopperChain.objects.all().order_by(
        'hopperchain_name'
    )
    context = {'hopperchain_list': hopperchain_list}
    return ds.render(request, 'djff/hopperchain_index.html', context)


def hopperchain_delete_hopper(request, chain_id, hopper_index):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    del chain.hopperchain_spec[hopper_index]
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_insert_hopper(request, chain_id, hopper_index):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    chain.hopperchain_spec.insert(hopper_index, ('null', dict()))
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_up(request, chain_id, hopper_index):
    logger.info(
        "Moving hopper {} in chain {} up.\n".format(
            hopper_index,
            chain_id,
        )
    )
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    if hopper_index > 0:
        (chain.hopperchain_spec[hopper_index],
            chain.hopperchain_spec[hopper_index-1]) = (
                chain.hopperchain_spec[hopper_index-1],
                chain.hopperchain_spec[hopper_index]
            )
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_down(request, chain_id, hopper_index):
    logger.info(
        "Moving hopper {} in chain {} down.\n".format(
            hopper_index,
            chain_id,
        )
    )
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    if hopper_index < len(chain.hopperchain_spec) - 1:
        (chain.hopperchain_spec[hopper_index],
            chain.hopperchain_spec[hopper_index+1]) = (
                chain.hopperchain_spec[hopper_index+1],
                chain.hopperchain_spec[hopper_index]
            )

    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_renamer(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    chain.hopperchain_name = request.POST['new_name']
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_rename(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    return ds.render(
        request,
        'djff/hopperchain_rename.html',
        {'chain': chain}
    )


def hopperchain_edit(request, chain_id):
    logger.info("Edit page loaded.\n")
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    hopper_classes = CLASS_PARAMS.keys()
    hopper_classes.remove('null')

    for hop_type, hop_params in chain.hopperchain_spec:
        def_params = CLASS_PARAMS[hop_type]['params']
        for key in def_params:
            if key not in hop_params:
                if def_params[key][1]:
                    hop_params[key] = def_params[key][1]
                else:
                    hop_params[key] = ''

    return ds.render(
        request,
        'djff/hopperchain_edit.html',
        {
            'chain': chain,
            'hopper_classes': hopper_classes,
        }
    )


def hopperchain_editor(request, chain_id):
    logger.info("Editing chain {}.".format(chain_id))
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    for key, value in request.POST.iteritems():
        if 'editparam ' == key[:10]:
            hopper_index, param_name = key[10:].split(" ")
            hopper_index = int(hopper_index)
            chain.hopperchain_spec[hopper_index][1][param_name] = value

    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_set(request, chain_id, hopper_index, hop_type):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    chain.hopperchain_spec[hopper_index] = (
        hop_type,
        CLASS_PARAMS[hop_type]['defaults']
    )
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_new(request):
    chain = HopperChain()
    chain.hopperchain_spec = [('null', dict())]
    chain.hopperchain_name = "New HopperChain"
    chain.save()

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:hopperchain_rename',
                    args=(chain.id,))
    )


def hopperchain_deleter(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    chain.hopperchain_name = request.POST['new_name']
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_preview_image(request, chain_id):
    src_img = _file_path_to_numpy_array('sample-DATA.jpg')

    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    image_source = djff.utils.hopperchain.ImageSource([src_img])

    real_hc = djff.utils.hopperchain.HopperChain(
        chain.hopperchain_spec,
        source_obj=image_source
    )

    img = real_hc.next()[0]
    return _image_response_from_numpy_array(img, 'jpg')
