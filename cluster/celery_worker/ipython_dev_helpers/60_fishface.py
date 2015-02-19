import fishface_image
import tasks
import os

HOME = os.path.expanduser('~')
ALT_ROOT = HOME

def ff_jpeg_loader(name='hard'):
    with open(os.path.join(ALT_ROOT, 'ff_{}_image.jpg'.format(name)), 'rb') as jpeg_file:
        jpeg = jpeg_file.read()
    return jpeg

cal_jpeg = ff_jpeg_loader('cal')
easy_jpeg = ff_jpeg_loader('easy')
hard_jpeg = ff_jpeg_loader()