#!/usr/bin/env python

"""
The objects in this module handle image processing on the macro level.
"""
import os
import glob

import cv2

from djff.utils import hoppers


def _find_jpgs_in_dir(directory):
    """
    Finds files with .jpg and .jpeg extensions in the specified
    directory.

    :param directory: The directory to look for JPGs in.
    :return: List of JPGs in the specified directory.
    """
    return (
        glob.glob(os.path.join(directory, "*.jpg")) +
        glob.glob(os.path.join(directory, "*.jpeg"))
    )


def spec_to_string(spec):
    """
    Converts a hopperchain spec into a string suitable for printing
    or database storage.

    :param spec: The hopperchain spec to process.
    :return: A string based on the provided hopperchain spec.
    """
    return '#'.join([hoppers.spec_to_string(hop_spec) for
                     hop_spec in spec])


def string_to_spec(string):
    """
    Converts a string formatted by spec_to_string back into a
    hopperchain spec.

    :param string: The string to process.
    :return: A hopperchain spec based on the string.
    """
    spec = list()
    hopper_spec_strings = string.split('#')
    for spec_string in hopper_spec_strings:
        spec.append(hoppers.string_to_spec(spec_string))
    return spec


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
        """Part of the iterable protocol."""
        return self

    def next(self):
        """
        Part of the iterable protocol.  Returns the image in the list
        until the list runs dry.
        """
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
        """Part of the iterable protocol."""
        return self

    def next(self):
        """
        Part of the iterable protocol.  Returns the next image from the
        list until the list runs dry.
        """
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

    :param hopperchain_spec iter: An iterable of hopper specifications.
                            Each hopper spec is a pair: a string ID for
                            the class of hopper to create, and a
                            dictionary of parameters to pass to it.
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

    def __init__(self, hopperchain_spec,
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
        self._orig_chain_spec = hopperchain_spec
        self.append_hoppers(hopperchain_spec)

    def __iter__(self):
        """Part of the iterable protocol."""
        return self

    def next(self):
        """Returns the next image after the chain processes it."""
        try:
            image, meta_data = self._hopper_list[-1].next()
        except StopIteration:
            raise
        return image, meta_data

    @property
    def spec(self):
        """
        Returns a hopperchain spec (which is a tuple of hopper
        specs).
        """
        return tuple(hop.spec for hop in self._hopper_list)

    def append_hoppers(self, hopperchain_spec):
        """
        Append hoppers to the chain according to the hopperchain spec
        provided.

        :param hopperchain_spec: The chain spec to
        :return:
        """
        for hopper_class_str, hopper_param in hopperchain_spec:
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

    def get_hopper(self, index):
        """
        Gets a specific hopper spec from the list of hoppers
        in the chain.

        :param index: The index of the hopper to retrieve.
        :return: The spec of the retrieved hopper.
        """
        return self._hopper_list[index].spec

    def set_hopper(self, index, hopper_spec):
        """
        Replaces a specific hopper in the chain with a new hopper
        generated by hopper_spec.

        :param index: Which hopper to replace.
        :param hopper_spec: The hopper spec of the replacement hopper.
        """
        hopper_class_str, hopper_param = hopper_spec
        hopper_class = hoppers.CLASS_IDS[hopper_class_str]

        if index == 0:
            source = self._image_source
        else:
            source = self._hopper_list[index-1]

        self._hopper_list[index] = hopper_class(source, **hopper_param)

        new_hopper = self._hopper_list[index]

        try:
            self._hopper_list[index+1].set_source(new_hopper)
        except IndexError:
            pass

    def insert_hoppers(self, position, chain_spec=None, number=None):
        """
        Inserts hoppers into a hopper chain.

        Either chain_spec or number must be specified.  If chain_spec
        is given, then its length overrides number.

        :param position: The position in the chain at which to insert
                         the new hoppers.
        :param chain_spec: The chain spec of the hoppers to insert.
        :param number: The number of null hoppers to insert.
        :return:
        """
        if number is None and chain_spec is None:
            raise Exception("Must specify either the number of null " +
                            "hoppers to insert or a chain_spec " +
                            "specifying exactly what to insert.")

        if chain_spec is not None:
            number = len(chain_spec)

        for i in range(number):
            if i + position == 0:
                source = self._image_source
            else:
                source = self._hopper_list[i+position-1]

            if chain_spec is not None:
                hopper_class_str, hopper_params = chain_spec[i]
                hopper_class = hoppers.CLASS_IDS[hopper_class_str]
            else:
                hopper_class = hoppers.Hopper
                hopper_params = {}

            self._hopper_list.insert(
                position+i,
                hopper_class(
                    source,
                    **hopper_params
                )
            )

    def delete_hoppers(self, position, number=1):
        """
        Delete a specified number of hoppers from a specific location
        in the chain.

        :param position: The position to delete hoppers from.
        :param number: The number of hoppers to delete.
        :return:
        """
        if position+number > len(self):
            raise Exception(
                "Cannot remove {} hoppers from position {}, because " +
                "only {} hoppers exist at that location".format(
                    number,
                    position,
                    len(self) - position + 1
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
        """Returns the length of the list of hoppers in the chain."""
        return len(self._hopper_list)
