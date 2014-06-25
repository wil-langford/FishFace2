import hoppers
import nose.tools as nt
import numpy as np
import cv2

TEST_IMAGES = {
    'grayscale-blackfill-1x1': np.array([[0]],
                                        dtype=np.uint8),
    'grayscale-blackfill-3x3': np.array([[0, 0, 0],
                                         [0, 0, 0],
                                         [0, 0, 0]],
                                        dtype=np.uint8),
    'grayscale-whitetop-2x2': np.array([[255, 255],
                                        [0, 0]],
                                       dtype=np.uint8)
}


class FakeSource(object):
    """
    Because testing the hoppers shouldn't depend on the HopperChain.

    This is a fake iterator.  It is initialized with a single numpy
    array and only returns it once before raising StopIteration.
    """
    def __init__(self, array):
        self._array = array.copy()
        self._first_run = True

    def __iter__(self):
        return self

    def next(self):
        if self._first_run:
            self._first_run = False
            return self._array
        else:
            raise StopIteration


class TestHoppers(object):
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

    def teardown(self):
        """
        This method is run once after _each_ test method is executed
        """

    def test_hopper_base(self):
        source = FakeSource(TEST_IMAGES['grayscale-blackfill-1x1'])
        hop = hoppers.Hopper(source)
        for output_image in hop:
            nt.assert_true(np.array_equal(
                TEST_IMAGES['grayscale-blackfill-1x1'],
                output_image)
            )

    def test_scale_by_factor_of_3(self):

        source = FakeSource(TEST_IMAGES['grayscale-blackfill-1x1'])
        hop = hoppers.HopperScale(source, factor=3)
        for output_image in hop:
            nt.assert_true(np.array_equal(
                TEST_IMAGES['grayscale-blackfill-3x3'],
                output_image)
            )


        whitetop_times_3 = cv2.resize(
            TEST_IMAGES['grayscale-whitetop-2x2'],
            (6,6)
        )
        source = FakeSource(TEST_IMAGES['grayscale-whitetop-2x2'])
        hop = hoppers.HopperScale(source, factor=3)
        for output_image in hop:
            nt.assert_true(np.array_equal(
                whitetop_times_3,
                output_image)
            )



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
    source = FakeSource(TEST_IMAGES['grayscale-blackfill-1x1'])
    for image in source:
        print image


if __name__ == '__main__':
    main()