from ast import literal_eval as eval
import logging

import django.shortcuts as ds
import django.http as dh
import django.core.urlresolvers as dcu
import django.core.files.storage as dcfs

from djff.models import Experiment, Image, ImageAnalysis
from djff.models import HopperChain

from fishface.hoppers import CLASS_PARAMS
import fishface.hopperchain

import cv2
import numpy as np

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s %(levelname)s %(message)s',
    filename = '/tmp/djangoLog.log',)

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
    response = dh.HttpResponse(out, mimetype="image/{}".format(
        extension
    ))
    return response


def index(request):
    pass


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

    chain.hopperchain_spec[hopper_index] = (hop_type, dict())
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_new(request):
    chain = HopperChain()
    chain.hopperchain_spec = [ ('null', dict())]
    chain.hopperchain_name = "New HopperChain"
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_rename',
                                               args=(chain.id,)))


def hopperchain_deleter(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)

    chain.hopperchain_name = request.POST['new_name']
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))

def hopperchain_preview_image(request, chain_id):
    try:
        chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    except dh.Http404:
        img = np.ones((100,100,3),dtype=np.uint8) * 150
        return _image_response_from_numpy_array(img, 'jpg')

    image_source = fishface.hopperchain.ImageSource(
        [np.ones((100,100,3)) * 0]
    )

    real_hc = fishface.hopperchain.HopperChain(
        chain.hopperchain_spec,
        source_obj=image_source
    )

    img, metadata = real_hc.next()
    return _image_response_from_numpy_array(img, 'jpg')
