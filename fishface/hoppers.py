#!/usr/bin/env python

"""
This is the image processing subsystem of FishFace.

There are two major categories of objects in the image processing
subsystem of FishFace:

* Hoppers
    - Hoppers take an ImageFrame and return an ImageFrame as
      part of a HopperChain.
    - Each hopper subclass applies one image processing operation as an
      ImageFrame passes through it.
* HopperChain
    - A sequence of hoppers together with parameters for each.
    - A HopperChain takes an ImageSource object and returns
      processed images.
"""

import cv2

__author__ = 'wil-langford'


class Hopper(object):
    """
    This is the base class for the various hoppers.

    :param source iter: This is an iterable that returns numpy images
                        that this hopper will process.

    This hopper implements the iterable protocol.  It reads numpy
    images from its source and returns them unchanged when its
    .next() method is called.
    """

    def __init__(self, source, *args, **kwargs):
        self._source = source

    def __iter__(self):
        return self

    def next(self):
        """Returns the next image after the hopper processes it."""
        try:
            image = self._source.next()
        except StopIteration:
            raise
        return self._process(image)

    def _process(self, image):
        return image

class HopperScale(Hopper):
    """
    Scale a numpy image by a factor or a specific pixel size tuple.

    :param factor float: A floating point number indicating the scale
                         factor to apply. (default==1.0)
    :param new_size tuple: A tuple of length 2 containing ints.  The
                           tuple should be of the form (width,height).

    At least one of factor and new_size must be specified.  If both
    are given, factor takes precedence over new_size.
    """

    def __init__(self, source, factor=None, new_size=None, *args, **kwargs):
        super(HopperConvertToGrayscale, self).__init__(self, source)
        self._source = source

        try:
            arg_zero = args[0]
        except IndexError:
            arg_zero = False

        if arg_zero:
            try:
                if len(arg_zero) == 2:
                    self._new_size = arg_zero
            except TypeError:
                factor = float(arg_zero)
                if factor > 0:
                    factor = float(arg_zero)

        self._new_size = new_size
        self._factor = float(factor)

        if not self._new_size and not self._factor:
            raise Exception("No valid scaling factor or new size found.")

    def _process(self, image):
        if not self._new_size and self._factor:
            self._new_size = int(image.shape[0]*self._factor), int(image.shape[1]*self._factor)
        result = cv2.resize(image,self._new_size)

        return result


class HopperConvertToGrayscale(Hopper):
    """
    Convert a numpy image to a single color channel image.
    """

    def __init__(self, source, *args, **kwargs):
        super(HopperConvertToGrayscale, self).__init__(self, source)
        self._source = source

    def _process(self, image):
        if len(image.shape) == 3 and image.shape[2] == 3:
            result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        return result