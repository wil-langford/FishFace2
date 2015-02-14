import fishface_image
import tasks

def ff_jpeg_loader(name='data'):
    with open('/home/wsl/ff_{}_image.jpg'.format(name), 'rb') as jpeg_file:
        jpeg = jpeg_file.read()
    return (jpeg, tasks.decode_jpeg_string(jpeg))

cal_jpeg, cal_image = ff_jpeg_loader('cal')
data_jpeg, data_image = ff_jpeg_loader()