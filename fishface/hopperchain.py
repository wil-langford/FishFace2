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

class FileSource(object):
    """
    Get images from the filesystem into a HopperChain.

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

        return (
            image,
            {
                'source_type': 'ImageSource',
                'source_filename': filename,
            }
        )


class ImageSource(object):
    """
    Feed an iterable of numpy arrays into the start of a HopperChain.

    :param file_list iter: A list of image filenames to read. If the
                           file_dir parameter is given, the file_list
                           can contain bare filenames without path info.
    :param file_dir str: A string containing the directory containing
                         the data images to read.  If the file_list
                         parameter is given, only those files are read
                         from the file_dir directory.  If not, every
                         file matching "*.jpg" in file_dir is read.
    """

    def __init__(self, source_list):
        self._source_list = source_list
        self._index = 0

    def __iter__(self):
        return self

    def next(self):
        try:
            image = self._source_list[self._index]
            self._index += 1
        except IndexError:
            raise StopIteration

        return (
            image,
            {
                'source_type': 'ImageSource'
            }
        )


class HopperChain(object):
    """
    Manage multiple hoppers in series.

    :param chain_spec iter: An iterable of hopper specifications.  Each
                            hopper spec is a pair: a string ID for the
                            class of hopper to create, and a dictionary
                            of parameters to pass to it.
    :param source_list iter: This is passed directly to FileSource as
                             the file_list parameter.
    :param source_dir iter: This is passed directly to FileSource as
                            the file_dir parameter.

    The HopperChain creates an FileSource based on the source_list
    and/or source_dir parameters.  It also creates a series of hopper
    classes to perform a series of image processing operations on each
    numpy.array image returned from the FileSource.  The source for the
    first hopper in the chain is the FileSource, and the source for
    each hopper after that is the previous hopper.

    Output of the HopperChain itself is via the iterable protocol.
    That is, "for output_image in hopper_chain: ..."
    """

    def __init__(self, chain_spec,
                 source_obj=None,
                 source_list=None, source_dir=None):
        if isinstance(source_obj, (ImageSource, FileSource)):
            self._image_source = source_obj
        elif source_list is not None or source_dir is not None:
            self._image_source = FileSource(file_list=source_list,
                                       file_dir=source_dir)
        else:
            raise Exception("You must specify a source for the " +
                            "HopperChain.")

        self._hopper_list = list()
        self._orig_chain_spec = chain_spec
        print chain_spec
        self.append_hoppers(chain_spec)

    def __iter__(self):
        return self

    def next(self):
        """Returns the next image after the chain processes it."""
        try:
            image, meta_data = self._hopper_list[-1].next()
        except StopIteration:
            raise
        return (image, meta_data)

    def chain_spec(self):
        return tuple(hop.spec for hop in self._hopper_list)

    def append_hoppers(self, chain_spec):
        print chain_spec
        for hopper_class_str, hopper_param in chain_spec:
            if len(self._hopper_list) == 0:
                source = self._image_source
            else:
                source = self._hopper_list[-1]

            hopper_class = hoppers.CLASS_IDS[hopper_class_str]

            self._hopper_list.append(
                hopper_class(
                    source,
                    **hopper_param
                )
            )

            self._hopper_list[-1].spec = (hopper_class_str,
                                          hopper_param)

    def get_hopper(self, index):
        return self._hopper_list[index].spec

    def set_hopper(self, index, hopper_class_str, hopper_param):
        hopper_class = hoppers.CLASS_IDS[hopper_class_str]

        if index == 0:
            source = self._image_source
        else:
            source = self._hopper_list[index-1]

        self._hopper_list[index] = hopper_class(source, **hopper_param)

        new_hopper = self._hopper_list[index]
        new_hopper.spec = (hopper_class_str, hopper_param)

        try:
            self._hopper_list[index+1].set_source(new_hopper)
        except IndexError:
            pass

    def insert_hoppers(self, position, chain_spec=None, number=None):
        if number is None and chain_spec is None:
            raise Exception("Must specify either the number of null " +
                            "hoppers to insert or a chain_spec " +
                            "specifying exactly what to insert.")

        if chain_spec is not None:
            number = len(chain_spec)

        for i in range(number):
            if i+position==0:
                source = self._image_source
            else:
                source = self._hopper_list[i+position-1]

            if chain_spec is not None:
                hopper_class_str, hopper_params = chain_spec[i]
                hopper_class = hoppers.CLASS_IDS[hopper_class_str]
            else:
                hopper_class = hoppers.Hopper
                hopper_params = {}

            self._hopper_list.insert(position+i,
                                     hopper_class(source,
                                                  **hopper_params)
            )


    def delete_hoppers(self, position, number=1):
        if position+number > self.len():
            raise Exception("Cannot remove {} hoppers from position " +
                            "{}, because only {} hoppers exist at " +
                            "that location".format(number,
                                              position,
                                              self.len() - position + 1
                                              )
        )

        if position == 0:
            source = self._image_source
        else:
            source = self._hopper_list[position].source

        for i in range(number):
            self._hopper_list.pop(position)

        self._hopper_list[position].set_source(source)

    def __len__(self):
        return len(self._hopper_list)