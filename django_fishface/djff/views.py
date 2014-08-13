import django.shortcuts as ds

from djff.models import Experiment, Image, ImageAnalysis
from djff.models import HopperChain


def index(request):
    hopperchain_list = HopperChain.objects.all().order_by(
        'hopperchain_name'
    )
    context = {'hopperchain_list': hopperchain_list}
    return ds.render(request, 'djff/index.html', context)