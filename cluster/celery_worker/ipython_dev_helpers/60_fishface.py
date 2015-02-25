import os
import site
import celery

import fishface_image
import django_tasks
from fishface_celery import app as celery_app

HOME = os.path.expanduser('~')
ALT_ROOT = HOME

djff_dir = os.path.join(ALT_ROOT, 'FishFace2', 'django_fishface')
site.addsitedir(djff_dir)
import djff.django_tasks as django_tasks

def ff_jpeg_loader(name='hard'):
    with open(os.path.join(ALT_ROOT, 'ff_{}_image.jpg'.format(name)), 'rb') as jpeg_file:
        jpeg = jpeg_file.read()
    return jpeg

cal_jpeg = ff_jpeg_loader('cal')
easy_jpeg = ff_jpeg_loader('easy')
hard_jpeg = ff_jpeg_loader()

cal = fishface_image.FFImage(source=cal_jpeg)
easy = fishface_image.FFImage(source=easy_jpeg)
hard = fishface_image.FFImage(source=hard_jpeg)