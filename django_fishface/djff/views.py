import logging
import numpy as np
import datetime
import json
import random
import math
import operator
# import time
# import threading

import cv2
import pytz
# import requests

import django.shortcuts as ds
import django.http as dh
import django.utils as du
import django.core.urlresolvers as dcu
import django.core.files.storage as dcfs
import django.views.decorators.csrf as csrf_dec
import django.utils.timezone as dut
import django.views.generic as dvg
import django.views.generic.edit as dvge
import django.db.models as ddm
from django.conf import settings

from djff.models import (
    Experiment,
    Image,
    Species,
    CaptureJobTemplate,
    CaptureJobRecord,
    PowerSupplyLog,
    Researcher,
    ManualTag,
    ManualVerification,
)

import djff.utils.telemetry as telemetry

IMAGERY_SERVER_IP = settings.IMAGERY_SERVER_HOST
IMAGERY_SERVER_PORT = settings.IMAGERY_SERVER_PORT

IMAGERY_SERVER_URL = 'http://{}:{}/'.format(
    IMAGERY_SERVER_IP,
    IMAGERY_SERVER_PORT
)

logger = logging.getLogger('djff.views')
logger.setLevel(logging.DEBUG)


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


def stats(request):
    xps = Experiment.objects.all().order_by('xp_start')
    cjrs = CaptureJobRecord.objects.all()
    researchers = Researcher.objects.all().order_by('name')

    xps_to_pass = dict()
    for xp in xps:
        xps_to_pass[xp.id] = {
            'id': xp.id,
            'name': xp.name,
            'slug': xp.slug,
            'cjrs': xp.capturejobrecord_set.all(),
            'actual_xp': xp,
        }

    cjrs_to_pass = dict()
    for cjr in cjrs:
        cjrs_to_pass[cjr.id] = {
            'slug': cjr.full_slug,
            'images': cjr.image_set.all(),
            'actual_cjr': cjr,
        }

    context = {
        'xps': xps_to_pass,
        'cjrs': cjrs_to_pass,
        'researchers': researchers,
    }
    return ds.render(request, 'djff/stats.html', context)


@csrf_dec.csrf_exempt
def receive_telemetry(request):

    payload = json.loads(request.POST['payload'])
    logger.info("Received telemetry from Raspi:\n{}".format(payload))

    if payload['command'] == 'post_image':
        xp = ds.get_object_or_404(Experiment, pk=payload['xp_id'])

        logger.info("Receiving image for experiment: {} ({})".format(xp.name, xp.slug))

        is_cal_image = (str(payload['is_cal_image']).lower()
                        in ['true', 't', 'yes', 'y', '1'])
        voltage = float(payload['voltage'])
        current = float(payload['current'])

        capture_timestamp = datetime.datetime.utcfromtimestamp(
            float(payload['capture_time'])).replace(tzinfo=dut.utc)

        try:
            cjr = ds.get_object_or_404(CaptureJobRecord, pk=int(payload['cjr_id']))
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
                payload['filename']
            ],
        )
        captured_image.save()

        logger.info("image stored with ID {}".format(captured_image.id))


    if payload['command'] == 'job_status_update':
        cjr = ds.get_object_or_404(CaptureJobRecord,
                                   pk=int(payload['cjr_id']))

        if payload['status'] == 'running':
            cjr.running = True
        else:
            cjr.running = False

        cjr.job_start = du.timezone.datetime.utcfromtimestamp(
            float(payload['start_timestamp'])
        ).replace(tzinfo=dut.utc)

        cjr.total = int(payload['total'])
        cjr.remaining = int(payload['remaining'])

        if payload['stop_timestamp']:
            cjr.job_stop = du.timezone.datetime.utcfromtimestamp(
                float(payload['stop_timestamp'])
            ).replace(tzinfo=dut.utc)

        cjr.save()

    if payload['command'] == 'power_supply_log':

        logger.info("posting power supply log:\n{}".format(payload))

        voltage_meas = float(payload['voltage_meas'])
        current_meas = float(payload['current_meas'])

        logger.info("voltage: {}, current: {}".format(voltage_meas, current_meas))

        psl = PowerSupplyLog()
        psl.voltage_meas = voltage_meas
        psl.current_meas = current_meas
        psl.save()

    response = dh.HttpResponse(json.dumps({'payload': ""}), content_type='text/json')
    response.status_code = 200

    return response


@csrf_dec.csrf_exempt
def telemetry_proxy(request):
    payload = request.POST
    logger.info('Telemetry proxy payload: {}'.format(payload))

    telemeter = telemetry.Telemeter()
    pi_reply = telemeter.post_to_raspi(payload)

    return dh.HttpResponse(content=json.dumps(pi_reply), content_type='application/json')

#################################
###  Tagging Interface Views  ###
#################################

def tagging_interface(request):

    all_researchers = Researcher.objects.all()
    researchers = [{'id': researcher.id, 'name': researcher.name, 'tag_score': researcher.tag_score }
                   for researcher in all_researchers ]


    context = {
        'researchers': researchers,
        'researchers_json': json.dumps(researchers),
    }
    return ds.render(request, 'djff/tagging_interface.html', context)

@csrf_dec.csrf_exempt
def tag_submit(request):
    payload = request.POST
    return_value = {
        'valid': True,
    }

    logger.debug("got tag_submit payload: {}".format(payload))

    if payload['researcher_id'] != 'NONE':
        researcher = Researcher.objects.get(pk=payload['researcher_id'])

        if (payload['image_id'] != 'DO_NOT_POST' and
                payload['start'] != 'NONE' and payload['end'] != 'NONE'):
            logger.info('making new ManualTag database entry')
            manual_tag = ManualTag()

            manual_tag.image = Image.objects.get(pk=payload['image_id'])
            manual_tag.researcher = researcher
            manual_tag.start = payload['start']
            manual_tag.end = payload['end']

            manual_tag.save()

        return_value['researcher_score'] = researcher.tag_score

        untagged_images = Image.objects.filter(is_cal_image=False).exclude(
            xp__name__contains='TEST_DATA').exclude(
            manualtag__researcher__id__exact=int(payload['researcher_id']))

        if untagged_images.count() == 0:
            return_value['valid'] = False
        else:
            return_value['untagged_images_count'] = untagged_images.count()
            max_id = untagged_images.aggregate(ddm.Max('id')).values()[0]
            min_id = math.ceil(max_id*random.random())
            untagged_image = untagged_images.filter(id__gte=min_id)[0]

            return_value.update({
                'id': untagged_image.id,
                'url': '{}{}'.format(settings.MEDIA_URL, untagged_image.image_file),
            })


    else:
        return_value['valid'] = False

    return dh.HttpResponse(json.dumps(return_value), content_type='application/json')

######################################
###  Verification Interface Views  ###
######################################

def verification_interface(request):

    all_researchers = Researcher.objects.all()
    researchers = [{'id': researcher.id, 'name': researcher.name }
                   for researcher in all_researchers ]


    context = {
        'researchers': researchers,
    }
    return ds.render(request, 'djff/verification_interface.html', context)

@csrf_dec.csrf_exempt
def verification_submit(request):
    payload = request.POST

    logger.debug("got verification_submit payload: {}".format(payload))

    researcher_id = payload['researcher_id']

    if researcher_id != 'NONE':
        ids = payload['tag_ids'].split(',')
        if len(ids) < 2:
            number_of_tags = len(ids)
        else:
            number_of_tags = None


        if (payload['tag_ids'] != 'DO_NOT_POST' and
                payload['tags_verified'] != 'DO_NOT_POST'):
            logger.info('making new database entry')

            verifieds = payload['tags_verified'].split(',')

            verified_ids = [x[0] for x in zip(ids,verifieds) if x[1]==1]
            unverified_ids = [x[0] for x in zip(ids,verifieds) if x[1]==0]

            for image_id in verified_ids:
                manual_verification = ManualVerification()

                manual_verification.image = Image.objects.get(pk=image_id)
                manual_verification.researcher = Researcher.objects.get(pk=researcher_id)

                manual_verification.save()

        unverified_tags = ManualTag.objects.filter().exclude(
            manualverification__researcher__id__exact=int(payload['researcher_id']))

        if unverified_tags.count() == 0 or number_of_tags is None:
            return_value = 0
        else:
            verify_these_unsorted = list()

            for i in range(number_of_tags):
                max_id = unverified_tags.aggregate(ddm.Max('id')).values()[0]
                min_id = math.ceil(max_id*random.random())
                unverified_tag = unverified_tags.filter(id__gte=min_id)[0]

                start = unverified_tag.start.split(',')
                end = unverified_tag.start.split(',')

                rotate_angle = - math.degrees(math.atan2(
                    int(end[1]) - int(start[1]),
                    int(end[0]) - int(start[0])
                ))

                verify_these_unsorted.append({
                    'id': unverified_tag.id,
                    'start': unverified_tag.start,
                    'end': unverified_tag.end,
                    'rotate_angle': rotate_angle,
                    'url': '{}{}'.format(settings.MEDIA_URL, unverified_tag.image.image_file),
                })

            verify_these = sorted(verify_these_unsorted, key=operator.itemgetter('id'))
            verify_ids = [x['id'] for x in verify_these]

            return_value = {
                'verify_these': verify_these,
                'tag_ids': verify_ids,
                'tag_image_urls': [x['url'] for x in verify_these],
                'verify_ids_text': ','.join([str(x) for x in verify_ids]),
                'tags_verified_text': ','.join(['0'] * len(verify_these)),
            }

    else:
        return_value = 0

    return dh.HttpResponse(json.dumps(return_value), content_type='application/json')


#############################
###  Capture Queue Views  ###
#############################

def cq_interface(request):

    cjts = CaptureJobTemplate.objects.all()
    job_specs = dict()
    for cjt in cjts:
        job_specs[cjt.id] = {
            'voltage': cjt.voltage,
            'current': cjt.current,
            'startup_delay': cjt.startup_delay,
            'interval': cjt.interval,
            'duration': cjt.duration
        }
    job_specs = json.dumps(job_specs)

    all_xps = Experiment.objects.all()
    xps = [xp for xp in all_xps if Image.objects.filter(xp_id=xp.id, is_cal_image=True)]
    xp_names = dict()
    xp_species = dict()
    for xp in xps:
        xp_names[xp.id] = "{} ({})".format(xp.name, xp.slug)
        xp_species[xp.id] = xp.species.shortname

    context = {
        'xps': xps,
        'xp_names_json': json.dumps(xp_names),
        'xp_species_json': json.dumps(xp_species),
        'job_specs': job_specs,
        'cjts': cjts,
        'raspi_telemetry_url': settings.TELEMETRY_URL,
    }
    return ds.render(request, 'djff/cq_interface.html', context)


@csrf_dec.csrf_exempt
def cjr_new_for_raspi(request):
    logger.debug("making new CJR with: {}".format(request.POST))
    cjr = CaptureJobRecord()

    cjr.xp_id = int(request.POST['xp_id'])
    cjr.voltage = float(request.POST['voltage'])
    cjr.current = float(request.POST['current'])

    cjr.running = True

    cjr.job_start = datetime.datetime.utcfromtimestamp(float(request.POST['start_timestamp'])).replace(
        tzinfo=pytz.utc)

    cjr.save()

    data = json.dumps({
        'cjr_id': cjr.id,
        'species': cjr.xp.species.shortname
    })

    return dh.HttpResponse(data, content_type='application/json')


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
        'species': xp.species.shortname,
        'no_reply': 1,
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
    if (not request.POST['is_cal_image'] == 'True' or request.POST.get('cal_ready', '') == 'True'):
        telemeter = telemetry.Telemeter()
        response = telemeter.post_to_raspi(payload)

        logger.debug("Post-request response: {}".format(response))

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_capture',
                    args=(response['xp_id'],))
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

    cjrs = CaptureJobRecord.objects.filter(xp__id=xp.id).order_by('job_start')

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

def insert_capturejob_into_queue(request):
    post = request.POST
    xp_id = post['xp_id']
    xp = ds.get_object_or_404(Experiment, pk=xp_id)

    payload = {
        'command': 'insert_job',
        'position': post['position'],
        'xp_id': xp.id,
        'species': xp.species.shortname,
        'voltage': post['voltage'],
        'current': post['current'],
        'duration': post['duration'],
        'interval': post['interval'],
        'startup_delay': post['startup_delay'],
    }

    telemeter = telemetry.Telemeter()
    response = telemeter.post_to_raspi(payload)
    return response


def abort_running_job(request):
    telemeter = telemetry.Telemeter()
    response = telemeter.post_to_raspi({'command': 'abort_running_job'})

    running_jobs = CaptureJobRecord.objects.filter(running=True)
    for cjr in running_jobs:
        cjr.running = False
        cjr.save()

    xp_id = response.get('xp_id', False)
    cjr_id = response.get('cjr_id', False)

    if cjr_id and not xp_id:
        cjr = ds.get_object_or_404(CaptureJobRecord, pk=int(cjr_id))
        xp_id = cjr.xp_id

    if xp_id:
        return dh.HttpResponseRedirect(
            dcu.reverse('djff:xp_capture',
                        args=(xp_id,))
        )

    return dh.HttpResponseRedirect(dcu.reverse('djff:xp_index'))


################################
###  Internal Capture views  ###
################################


@csrf_dec.csrf_exempt
def receive_image(request):
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
