#!/usr/bin/env python

"""
The objects in this module handle image processing on the macro level.
"""

import hoppers
import cv2
import os
import glob

def _find_jpgs_in_dir(dir):
    return (glob.glob(os.path.join(dir,"*.jpg")) +
            glob.glob(os.path.join(dir,"*.jpeg"))
    )

class ImageSource(object):
    """
    Get images from the filesystem into HopperChains.

    :param file_list iter: A list of image filenames to read. If the
                           file_dir parameter is given, the file_list
                           can contain bare filenames without path info.
    :param file_dir str: A string containing the directory containing
                         the data images to read.  If the file_list
                         parameter is given, only those files are read
                         from the file_dir directory.  If not, every
                         file matching "*.jpg" in file_dir is read.
    """

    def __init__(self, file_list=None, file_dir=None):
        # Both file_list and file_dir are specified.
        if file_list is not None and file_dir is not None:
            self._file_list = file_list
            self._file_dir = file_dir
            self._source = (os.path.join(file_dir, file_name) for
                            file_name in file_list)

        # Only file_dir is specified.
        elif file_dir is not None and file_list is None:
            self._file_dir = file_dir
            self._file_list = _find_jpgs_in_dir(file_dir)
            self._source = (file_path for file_path in self._file_list)

        # Only file_list is specified.
        elif file_list is not None and file_dir is None:
            self._file_list = file_list
            self._source = (file_path for file_path in self._file_list)
        else:
            raise Exception("file_dir or file_list must be specified.")

    def __iter__(self):
        return self

    def next(self):
        try:
            filename = self._source.next()
        except StopIteration:
            raise

        image = cv2.imread(filename)

        return image

class HopperChain(object):
    """
    Manage multiple hoppers in series.

    :param chain_spec iter: An iterable of hopper specifications.  Each
                            hopper spec is a pair: a string ID for the
                            class of hopper to create, and a dictionary
                            of parameters to pass to it.
    :param source_list iter: This is passed directly to ImageSource as
                             the file_list parameter.
    :param source_dir iter: This is passed directly to ImageSource as
                            the file_dir parameter.

    The HopperChain creates an ImageSource based on the source_list
    and/or source_dir parameters.  It also creates a series of hopper
    classes to perform a series of image processing operations on each
    numpy.array image returned from the ImageSource.  The source for the
    first hopper in the chain is the ImageSource, and the source for
    each hopper after that is the previous hopper.

    Output of the HopperChain itself is via the iterable interface.
    That is, "for output_image in hopper_chain: ..."
    """

    def __init__(self, chain_spec, source_list=None, source_dir=None):
        self._source = ImageSource(file_list=source_list,
                                   file_dir=source_dir)
        self._hopper_list = list()
        self.append_hoppers(chain_spec)

    def __iter__(self):
        return self

    def next(self):
        """Returns the next image after the chain processes it."""
        try:
            image = self._hopper_list[-1].next()
        except StopIteration:
            raise
        return image

    def append_hoppers(self, chain_spec):
        for hopper_class_str, hopper_spec in chain_spec:
            if len(self._hopper_list) == 0:
                source = self._source
            else:
                source = self._hopper_list[-1]

            hopper_class = hoppers.CLASS_IDS[hopper_class_str]

            self._hopper_list.append(
                hopper_class(
                    source,
                    **hopper_spec
                )
            )
