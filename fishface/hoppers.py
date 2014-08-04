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
    - A HopperChain takes an FileSource object and returns
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

    def __init__(self, source):
        self.source = source
        self.spec = ("null", {})

    def __iter__(self):
        return self

    def __str__(self):
        return "Hopper"

    def next(self):
        """Returns the next image after the hopper processes it."""
        try:
            image, meta_data = self.source.next()
        except StopIteration:
            raise
        return (self._process(image), meta_data)

    def _process(self, image):
        return image

    def set_source(self, source):
        self.source = source


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

    def __init__(self, source, factor=None,
                 new_size=None, *args):
        super(HopperScale, self).__init__(source)

        # Look for an extra positional argument, figure out whether it's
        # a factor or a new_size, and react accordingly.
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
            raise Exception("No valid scaling factor or size found.")

        self.spec = ("scale", {"new_size": self._new_size,
                                "factor": self._factor})

    def _process(self, image):
        if not self._new_size and self._factor:
            new_size = (int(image.shape[0]*self._factor),
                              int(image.shape[1]*self._factor))
        elif self._new_size:
            new_size = self._new_size

        # The size tuple has to be reversed to fit cv2.resize's
        # size specification.
        result = cv2.resize(image, tuple(reversed(new_size)))

        return result

    def __str__(self):
        return "HopperScale:newsize={}:factor={}:".format(
            self._new_size, self._factor
        )


class HopperConvertToGrayscale(Hopper):
    """
    Convert a numpy image to a single color channel image.
    """

    def __init__(self, source):
        super(HopperConvertToGrayscale, self).__init__(source)

        self.spec = ("grayscale", {})

    def _process(self, image):
        if len(image.shape) == 3 and image.shape[2] == 3:
            result = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 1:
            result = image
        else:
            result = False

        return result

    def __str__(self):
        return "HopperConvertToGrayscale"


class HopperThreshold(Hopper):
    """
    Threshold an image leaving pixels either white or black.

    :param thresh int: An integer in the range 0-255.

    Any pixel with a value greater than the threshold is set to max
    brightness, and all other pixels are colored black.
    """

    def __init__(self, source, thresh):
        super(HopperThreshold, self).__init__(source)
        self._thresh = thresh

        self.spec = ("threshold", {"thresh": thresh})

    def _process(self, image):
        returned_thresh, result = cv2.threshold(image,
                               thresh=self._thresh,
                               maxval=255,
                               type=cv2.THRESH_BINARY
        )

        return result

    def __str__(self):
        return "HopperThreshold:threshold={}".format(self._thresh)

class HopperInvert(Hopper):
    """
    """

    def __init__(self, source):
        super(HopperInvert, self).__init__(source)

        self.spec = ("invert", {})

    def _process(self, image):
        result = 255 - image
        return result

    def __str__(self):
        return "HopperInvert"

CLASS_IDS = {
    "null": Hopper,
    "scale": HopperScale,
    "grayscale": HopperConvertToGrayscale,
    "threshold": HopperThreshold,
    "invert": HopperInvert
}
