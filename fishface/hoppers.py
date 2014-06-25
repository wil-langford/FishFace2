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
import itertools

__author__ = 'wil-langford'


class Hopper(object):
    """
    This is the base class for the various hoppers.
    """

    def __init__(self, *args, **kwargs):
        pass