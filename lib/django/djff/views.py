import logging
import numpy as np
import datetime
import json
import random
import math

import cv2
import pytz

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

import etc.fishface_config as ff_conf

from lib.django.djff.models import (
    Experiment,
    Image,
    Species,
    CaptureJobTemplate,
    CaptureJobRecord,
    PowerSupplyLog,
    Researcher,
    ManualTag,
    ManualVerification,
    CaptureJobQueue,
    PriorityManualImage,
)

from lib.fishface_celery import celery_app


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
    return dh.HttpResponse(out, content_type="image/{}".format(extension))


def _image_response_from_bytes_io(img, extension):
    """
    Returns an HttpResponse with an image mimetype based on the
    extension given.

    :param img: The numpy array to serve as an image.
    :param extension: "jpg" and "png" work.  Others can be tried at
                      your own risk.
    """
    response = dh.HttpResponse(img.read(), content_type="image/{}".format(
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


#
# General Views
#


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
            'cjrs': xp.capturejobrecord_set.all().order_by('id'),
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


def celery_proxy(request):
    payload = request.POST
    result_return = payload.get('result_return')
    result_timeout = payload.get('result_timeout')
    result_timeout = result_timeout if result_timeout else 15
    task_name = payload.get('task_name')
    kwargs = json.loads(payload.get('kwargs', '{}'))

    print 'type {} value {}'.format(type(kwargs), kwargs)

    celery_result = celery_app.send_task(
        task_name,
        kwargs=kwargs
    )

    if result_return:
        logger.warning('waiting for results')
        result = celery_result.get(timeout=result_timeout)
    else:
        result = False

    return dh.HttpResponse(content=json.dumps(result), content_type='application/json')


#
# Tagging Interface Views
#


def tagging_interface(request):

    all_researchers = Researcher.objects.all()
    researchers = [{
                       'id': researcher.id,
                       'name': researcher.name,
                       'tag_score': researcher.tag_score,
                       'bad_tags': researcher.bad_tags,
                       'good_tags': researcher.verified_tags
                   }
                   for researcher in all_researchers]

    context = {
        'researchers': researchers,
        'researchers_json': json.dumps(researchers),
        'resolution_json': json.dumps(ff_conf.CAMERA_RESOLUTION),
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

        return_value['researcher_all_tags'] = researcher.all_tags_count
        return_value['researcher_bad_tags'] = researcher.bad_tags
        return_value['researcher_good_tags'] = researcher.verified_tags
        return_value['researcher_unverified_tags'] = researcher.unverified_tags
        return_value['researcher_tags_undergone_verification'] = researcher.all_tags_count - researcher.unverified_tags
        return_value['researcher_good_rate'] = researcher.accuracy_score
        return_value['researcher_bad_rate'] = researcher.antiaccuracy_score

        return_value.update(PriorityManualImage.untagged_image(payload))
        if return_value['id']:
            untagged_image = Image.objects.get(pk=return_value['id'])
            return_value['url'] = '{}{}'.format(settings.MEDIA_URL,
                                                untagged_image.image_file)

    else:
        return_value['valid'] = False
        return_value['reason'] = 'no_researcher'

    return dh.HttpResponse(json.dumps(return_value), content_type='application/json')


#
# Verification Interface Views
#


def verification_interface(request):

    all_researchers = Researcher.objects.all()
    researchers = [{'id': researcher.id, 'name': researcher.name}
                   for researcher in all_researchers]

    all_tags = ManualTag.objects.all()

    context = {
        'researchers': researchers,
        'tags': all_tags,
    }
    return ds.render(request, 'djff/verification_interface.html', context)


@csrf_dec.csrf_exempt
def verification_submit(request):
    payload = request.POST
    return_value = {
        'valid': True,
    }

    logger.debug("got verification_submit payload: {}".format(payload))

    researcher_id = payload['researcher_id']

    if researcher_id != 'NONE':
        if payload['num_tiles']:
            number_of_tiles = int(payload['num_tiles'])
        else:
            number_of_tiles = None

        if (payload['tag_ids'] != 'DO_NOT_POST' and
                payload['tags_verified'] != 'DO_NOT_POST' and
                number_of_tiles is not None):
            ids_and_verifications = zip(
                payload['tag_ids'].split(','),
                payload['tags_verified'].split(','),
            )

            ids, verifications = zip(*[x for x in ids_and_verifications if x[0] != 'NONE'])

            ids_set = set(ids)
            antiverified_tag_ids = set([x[0] for x in zip(ids, verifications) if x[1] == '0'])
            verified_tag_ids = ids_set - antiverified_tag_ids

            logger.debug('verified_tag_ids {}'.format(str(verified_tag_ids)))
            logger.debug('antiverified_tag_ids {}'.format(str(antiverified_tag_ids)))

            for tag_id in verified_tag_ids:
                logger.info('adding verification for tag id {}'.format(tag_id))
                manual_verification = ManualVerification()

                manual_verification.tag = ManualTag.objects.get(pk=tag_id)
                manual_verification.researcher = Researcher.objects.get(pk=researcher_id)

                manual_verification.save()

            logger.info('Tags antiverified: {}'.format(antiverified_tag_ids))
            for tag_id in antiverified_tag_ids:
                logger.info("Deleting antiverified tag with id {}".format(tag_id))
                antiverified_tag = ManualTag.objects.get(pk=tag_id)
                antiverified_tag.delete()

        unverified_tags = list(set(ManualTag.objects.filter().exclude(
            manualverification__researcher__id__exact=int(payload['researcher_id']))))
        random.shuffle(unverified_tags)
        if number_of_tiles is not None:
            unverified_tags = unverified_tags[:number_of_tiles]

        if len(unverified_tags) == 0 or number_of_tiles is None:
            return_value['valid'] = False
            return_value['reason'] = 'zero_unverified'
        else:
            verify_these = list()

            for tag in unverified_tags:
                verify_these.append({
                    'id': tag.id,
                    'url': dcu.reverse(
                        'djff:manual_tag_verification_image',
                        args=(tag.id,)
                    ),
                })

            short_by = number_of_tiles - len(verify_these)
            if short_by > 0:
                verify_these.extend([
                    {
                        'id': 'NONE',
                        'url': settings.STATIC_URL + 'djff/no_image.png'
                    }
                ] * short_by)

            verify_ids = [x['id'] for x in verify_these]

            return_value.update({
                'verify_these': verify_these,
                'tag_ids': verify_ids,
                'tag_image_urls': [x['url'] for x in verify_these],
                'verify_ids_text': ','.join([str(x) for x in verify_ids]),
                'tags_verified_text': ','.join(['1'] * len(verify_these)),
            })

    else:
        return_value['valid'] = False
        return_value['reason'] = 'no_researcher'

    return dh.HttpResponse(json.dumps(return_value), content_type='application/json')


#
# Capture Queue Views
#


def cq_interface(request):

    cjts = CaptureJobTemplate.objects.all().order_by()
    cjt_ids = [cjt.id for cjt in cjts]
    job_specs = dict()
    for cjt in cjts:
        job_specs[cjt.id] = {
            'id': cjt.id,
            'voltage': cjt.voltage,
            'current': cjt.current,
            'startup_delay': cjt.startup_delay,
            'interval': cjt.interval,
            'duration': cjt.duration,
            'job_spec': cjt.job_spec,
            'description': cjt.description,
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
        'cjt_ids': cjt_ids,
    }
    return ds.render(request, 'djff/cq_interface.html', context)


def cjqs(request):
    cjqs_ = CaptureJobQueue.objects.all()
    cjq_ids = [cjq.id for cjq in cjqs_]
    queues = dict()
    for cjq in cjqs_:
        queues[cjq.id] = {
            'id': cjq.id,
            'name': cjq.name,
            'comment': cjq.comment,
            'queue': cjq.queue,
        }

    payload = json.dumps({
        'cjq_ids': cjq_ids,
        'cjqs': queues
    })

    return dh.HttpResponse(payload, content_type='application/json')


def cq_builder(request):
    cjts = CaptureJobTemplate.objects.all()
    cjt_ids = [cjt.id for cjt in cjts]

    job_specs = dict()
    for cjt in cjts:
        job_specs[cjt.id] = {
            'voltage': cjt.voltage,
            'current': cjt.current,
            'startup_delay': cjt.startup_delay,
            'interval': cjt.interval,
            'duration': cjt.duration,
            'job_spec': cjt.job_spec,
            'capture': cjt.interval > 0,
            'description': cjt.description,
        }
    job_specs = json.dumps(job_specs)

    context = {
        'job_specs': job_specs,
        'cjts': cjts,
        'cjt_ids': cjt_ids,
        'resolution_json': json.dumps(ff_conf.CAMERA_RESOLUTION),
    }
    return ds.render(request, 'djff/cq_builder.html', context)


def cjq_saver(request):
    data = json.loads(request.POST.get('payload_json'))

    if data.get('delete', False):
        cjq = CaptureJobQueue.objects.get(pk=int(data['cjq_id']))
        cjq.delete()

        payload = json.dumps({
            'deleted': 1,
        })
    else:
        cjq_id = int(data['cjq_id'])

        if cjq_id:
            cjq = CaptureJobQueue.objects.get(pk=cjq_id)
        else:
            cjq = CaptureJobQueue()

        cjq.name = data['name']
        cjq.queue = data['queue']
        cjq.comment = data['comment']
        cjq.save()

        payload = json.dumps({
            'cjq_id': cjq.id,
            'name': cjq.name,
            'comment': cjq.comment
        })

    return dh.HttpResponse(payload, content_type='application/json')


@csrf_dec.csrf_exempt
def cjr_new_for_raspi(request):
    logger.info("making new CJR with: {}".format(request.POST))
    cjr = CaptureJobRecord()

    cjr.xp_id = int(request.POST['xp_id'])
    cjr.voltage = float(request.POST['voltage'])
    cjr.current = float(request.POST['current'])

    cjr.running = True

    cjr.job_start = datetime.datetime.utcfromtimestamp(
        float(request.POST['start_timestamp'])).replace(tzinfo=pytz.utc)

    cjr.save()

    data = json.dumps({
        'cjr_id': cjr.id,
        'species': cjr.xp.species.shortname
    })

    return dh.HttpResponse(data, content_type='application/json')


def save_cjq(request):
    rp = request.POST
    logger.info("making new CJQ with: {}".format(rp))

    cjq = CaptureJobQueue()

    cjq.name = rp.name
    cjq.comment = rp.comment
    cjq.queue = rp.queue

    cjq.save()

    return dh.HttpResponse(status=201)


#
# Experiment views
#


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
        dcu.reverse('djff:xp_detail', args=(xp.id,))
    )


def xp_detail_cals(request, xp_id):
    cal_image_objs = Image.objects.filter(xp=xp_id, is_cal_image=True)
    cal_images_chunk = ''.join([image.linked_inline_image(thumb=True) for image in cal_image_objs])

    payload = json.dumps({
        'cal_images_chunk': cal_images_chunk,
    })

    return dh.HttpResponse(payload, content_type='application/json')


def xp_detail(request, xp_id):
    try:
        xp = ds.get_object_or_404(Experiment, pk=xp_id)
    except ds.Http404:
        return dh.HttpResponseRedirect(
            dcu.reverse(
                'djff:xp_new',
                args=tuple(),
            )
        )

    xp_images = Image.objects.filter(xp__id=xp_id)

    cal_images = xp_images.filter(is_cal_image=True)

    data_images = xp_images.filter(is_cal_image=False)

    cjts = CaptureJobTemplate.objects.all()

    running_jobs = CaptureJobRecord.objects.filter(running=True)

    cjrs = CaptureJobRecord.objects.filter(xp__id=xp.id).order_by('job_start')

    images_by_cjr = [(cjr_obj, Image.objects.filter(cjr__id=cjr_obj.id))
                     for cjr_obj in cjrs]

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


#
# Species views
#


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


#
# CaptureJobTemplate views
#


def cjt_index(request):
    cjts = CaptureJobTemplate.objects.all()
    cjt_ids = [cjt.id for cjt in cjts]

    context = {
        'cjts': cjts,
        'cjt_ids': json.dumps(cjt_ids),
    }

    return ds.render(request, 'djff/cjt_index.html', context)


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


def cjt_chunk(request, cjt_id):
    cjt = CaptureJobTemplate.objects.get(pk=cjt_id)
    cjt_cooked = {
        'id': cjt.id,
        'voltage': cjt.voltage,
        'current': cjt.current,
        'startup_delay': cjt.startup_delay,
        'interval': cjt.interval,
        'capture': cjt.interval > 0,
        'duration': cjt.duration,
        'job_spec': cjt.job_spec,
        'description': cjt.description,
        'pretty_print_duration': str(datetime.timedelta(seconds=cjt.duration))
    }

    context = {
        'cjt': cjt_cooked,
    }

    return ds.render(request, 'djff/cjt_chunk.html', context)


#
# Internal Capture views
#


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
                current=current,
                is_cal_image=is_cal_image,
                cjr=cjr,
            )
            captured_image.image_file=request.FILES[request.POST['filename']],

            captured_image.save()

            logger.info("image stored with ID {}".format(
                captured_image.id
            ))

    return dh.HttpResponseRedirect(
        dcu.reverse('djff:xp_index'),
    )


#
# Dynamic image views
#


def manual_tag_verification_image(request, tag_id):
    tag = ManualTag.objects.get(pk=tag_id)
    return _image_response_from_bytes_io(tag.verification_image, 'jpg')