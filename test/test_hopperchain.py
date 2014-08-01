import sys
sys.path.append('../fishface')

import hoppers
import hopperchain
import nose.tools as nt
import numpy as np
import cv2
import os
import tempfile
import shutil
import nose_const

TEST_IMAGES = nose_const.TEST_IMAGES


class TestHopperChain(object):
    """
    Tests for the HopperChain module.
    """
    @classmethod
    def setup_class(cls):
        """
        This method is run once for each class _before_ any
        tests are run.
        """

    @classmethod
    def teardown_class(cls):
        """
        This method is run once for each class _after_ all
        tests are run.
        """

    def setUp(self):
        """
        This method is run once before _each_ test method is executed.
        """
        self._tmp_dir = tempfile.mkdtemp(prefix="FishFaceTEST_")
        for image_name in TEST_IMAGES:
            image_path = os.path.join(self._tmp_dir,
                                      image_name + ".jpg")
            cv2.imwrite(image_path, TEST_IMAGES[image_name])

        self._sources = dict()
        for test_image_name in TEST_IMAGES:
            self._sources[test_image_name] = hopperchain.ImageSource(
                [TEST_IMAGES[test_image_name]]
            )

        self.inv_chain = hopperchain.HopperChain(
            (("invert", {}),
             ("invert", {}),
             ("invert", {})),
            source_obj=self._sources['grayscale-blackfill-1x1']
        )

    def teardown(self):
        """
        This method is run once after _each_ test method is executed
        """
        shutil.rmtree(self._tmp_dir)

    def test_filesource_by_dir(self):
        file_list = hopperchain._find_jpgs_in_dir(self._tmp_dir)
        source = hopperchain.FileSource(file_list=file_list)
        for image in source:
            nt.assert_is_instance(image, np.ndarray)

    def test_gray_scalehalf_thresh100_hopperchain(self):
        chain_spec = (
            ("grayscale", {}),
            ("scale", {"factor": 0.5}),
            ("threshold", {"thresh": 100})
        )

        hop_chain = hopperchain.HopperChain(chain_spec,
                                            source_dir="../eph/")

        out_tmp_dir = tempfile.mkdtemp(prefix="FishFaceTESTOUT_")
        for output_image in hop_chain:
            file_handle, file_name = tempfile.mkstemp(suffix=".jpg",
                                                      dir=out_tmp_dir)
            cv2.imwrite(file_name, output_image)

    def test_hopper_insert(self):
        chain_spec = (
            ("invert", {}),
            ("invert", {}),
        )

        hop_chain = hopperchain.HopperChain(chain_spec,
                                            source_dir="../eph/")
        hop_chain.insert_hoppers(
            1,
            (
                ("null", {}),
                ("null", {}),
            )
        )

        nt.assert_equal(4, len(hop_chain))

        hopper_classes = [hoppers.CLASS_IDS[short_name]
                          for short_name in
                          'invert null null invert'.split(' ')]
        for hop, cls in zip(hop_chain._hopper_list, hopper_classes):
            nt.assert_is_instance(hop, cls)

    def test_hopper_delete(self):
        chain_spec = (
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
        )

        hop_chain = hopperchain.HopperChain(chain_spec,
                                            source_dir="../eph/")

        nt.assert_equal(6, len(hop_chain))

        hopper_classes = [hoppers.CLASS_IDS[short_name]
                          for short_name in
                          'invert invert null invert'.split(' ')]
        hop_chain.delete_hoppers(1, 2)
        for hop, cls in zip(hop_chain._hopper_list, hopper_classes):
            nt.assert_is_instance(hop, cls)

        nt.assert_equal(4, len(hop_chain))

    def test_hopper_get(self):
        chain_spec = (
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
            ("null", {}),
        )

        hop_chain = hopperchain.HopperChain(chain_spec,
                                            source_dir="../eph/")

        hopper_class_strs = 'invert null'.split(' ')
        for i in range(len(hop_chain)):
            nt.assert_equal(
                hop_chain.get_hopper(i)[0],
                hopper_class_strs[i % 2]
            )

    def test_hopper_set(self):
        chain_spec = (
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
            ("null", {}),
            ("invert", {}),
            ("null", {}),
        )

        hop_chain = hopperchain.HopperChain(chain_spec,
                                            source_dir="../eph/")

        for i in range(0, 6, 2):
            hop_chain.set_hopper(i, 'null', {})

        for i in range(len(hop_chain)):
            nt.assert_equal(hop_chain.get_hopper(i)[0], 'null')

    # def test_return_true(self):
    #     a = A()
    #     nt.assert_equal(a.return_true(), True)
    #     nt.assert_not_equal(a.return_true(), False)
    #
    # def test_raise_exc(self):
    #     a = A()
    #     nt.assert_raises(KeyError, a.raise_exc, "A value")
    #
    # @nt.raises(KeyError)
    # def test_raise_exc_with_decorator(self):
    #     a = A()
    #     a.raise_exc("A message")


def main():
    pass

if __name__ == '__main__':
    main()
