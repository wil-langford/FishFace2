import django.shortcuts as ds
import django.http as dh
import django.core.urlresolvers as dcu

from djff.models import Experiment, Image, ImageAnalysis
from djff.models import HopperChain

def index(request):
    pass


def hopperchain_edit(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    return ds.render(
        request,
        'djff/hopperchain_edit.html',
        {'chain': chain}
    )


def hopperchain_detail(request, chain_id):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    return ds.render(
        request,
        'djff/hopperchain_detail.html',
        {'chain': chain}
    )


def hopperchain_index(request):
    hopperchain_list = HopperChain.objects.all().order_by(
        'hopperchain_name'
    )
    context = {'hopperchain_list': hopperchain_list}
    return ds.render(request, 'djff/hopperchain_index.html', context)


def hopperchain_delete(request, chain_id, hopper_index):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    del chain.hopperchain_spec[hopper_index]
    chain.save()

    return dh.HttpResponseRedirect(dcu.reverse('djff:hopperchain_edit',
                                               args=(chain.id,)))


def hopperchain_insert(request, chain_id, hopper_index):
    chain = ds.get_object_or_404(HopperChain, pk=chain_id)
    hopper_index = int(hopper_index)

    chain.hopperchain_spec.insert(hopper_index, ('null', dict()))
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

