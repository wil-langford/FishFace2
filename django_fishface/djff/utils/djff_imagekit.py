import PIL.Image

import imagekit as ik
import imagekit.processors as ikp
import imagekit.utils as iku
import imagekit.models as ikm

import djff_math as ffm

class RotateImage(object):
    def __init__(self, angle):
        self.angle = angle

    def process(self, image):
        return image.rotate(self.angle)


class ManualTagVerificationThumbnail(ik.ImageSpec):
    format = 'JPEG'
    options = {'quality': 60}

    def __init__(self, tag=None, *args, **kwargs):
        super(ManualTagVerificationThumbnail, self).__init__(*args, **kwargs)

        if tag is not None:
            self.tag = tag
        else:
            raise Exception("Need to specify a tag.")

    @property
    def processors(self):
        width = self.tag.image.image_file.width
        height = self.tag.image.image_file.height

        start = self.tag.int_start

        start_from_center = (
            start[0] - width / 2,
            start[1] - height / 2,
        )

        # rotate
        angle = self.tag.degrees
        rot_start_from_center = ffm.rotate_point(start_from_center, angle)
        rot_start = (
            rot_start_from_center[0] + width / 2,
            rot_start_from_center[1] + height / 2,
        )

        # crop
        top = int(rot_start[1] - height / 6)
        left = int(rot_start[0] - width * 3 / 12)

        return [
            RotateImage(angle),
            ikp.Crop(width/3, height/3, x=-left, y=-top),
        ]
