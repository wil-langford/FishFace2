import glob
import hoppers
import hopperchain
import nose.tools as nt
import numpy as np
import cv2
import os
import tempfile
import shutil

TEST_IMAGES = {
    'grayscale-blackfill-1x1': np.array([[0]],
                                        dtype=np.uint8),
    'grayscale-blackfill-3x3': np.array([[0, 0, 0],
                                         [0, 0, 0],
                                         [0, 0, 0]],
                                        dtype=np.uint8),
    'grayscale-whitetop-2x2': np.array([[255, 255],
                                        [0, 0]],
                                       dtype=np.uint8),
    'grayscale-fourtone-2x2': np.array([[255, 196],
                                        [128, 64]],
                                       dtype=np.uint8),
    'color-bluegray-1x1': np.array([[[160, 200, 240]]],
                                   dtype=np.uint8)
}


class TestHopperChain(object):
    """
    Tests for the HopperChain module.
    """
    @classmethod
    def setup_class(cls):
        """
        This method is run once for each class _before_ any
        tests are run
        """

    @classmethod
    def teardown_class(cls):
        """
        This method is run once for each class _after_ all
        tests are run
        """

    def setUp(self):
        """
        This method is run once before _each_ test method is executed
        """
        self._tmp_dir = tempfile.mkdtemp(prefix="FishFaceTEST_")
        for image_name in TEST_IMAGES:
            image_path = os.path.join(self._tmp_dir, image_name + ".jpg")
            cv2.imwrite(image_path, TEST_IMAGES[image_name])

    def teardown(self):
        """
        This method is run once after _each_ test method is executed
        """
        shutil.rmtree(self._tmp_dir)

    def test_imagesource_by_dir(self):
        file_list = hopperchain._find_jpgs_in_dir(self._tmp_dir)
        source = hopperchain.ImageSource(file_list=file_list)
        for image in source:
            nt.assert_is_instance(image, np.ndarray)
            print


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