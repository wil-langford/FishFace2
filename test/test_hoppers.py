import sys
sys.path.append('../fishface')

import hoppers
import nose.tools as nt
import numpy as np
import cv2
import nose_const

TEST_IMAGES = nose_const.TEST_IMAGES


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
            return (self._array, dict())
        else:
            raise StopIteration


class TestHoppers(object):
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

    def teardown(self):
        """
        This method is run once after _each_ test method is executed.
        """

    def test_hopper_base(self):
        source = FakeSource(TEST_IMAGES['grayscale-blackfill-1x1'])
        hop = hoppers.Hopper(source)
        nt.assert_equal(hop.spec, ('null', dict()))
        for output_image, meta_data in hop:
            nt.assert_true(np.array_equal(
                TEST_IMAGES['grayscale-blackfill-1x1'],
                output_image)
            )

    def test_scale_by_factor_of_3(self):

        source = FakeSource(
            TEST_IMAGES['grayscale-blackfill-1x1'].copy()
        )
        hop = hoppers.HopperScale(source, factor=3)
        nt.assert_equal(
            hop.spec,
            (
                'scale',
                {
                    'factor': 3,
                    'new_size': None
                }
            )
        )

        for output_image, meta_data in hop:
            nt.assert_true(np.array_equal(
                TEST_IMAGES['grayscale-blackfill-3x3'],
                output_image)
            )

        whitetop_times_3 = cv2.resize(
            TEST_IMAGES['grayscale-whitetop-2x2'].copy(),
            (6, 6)
        )
        source = FakeSource(
            TEST_IMAGES['grayscale-whitetop-2x2'].copy()
        )
        hop = hoppers.HopperScale(source, factor=3)
        for output_image, meta_data in hop:
            nt.assert_true(np.array_equal(
                whitetop_times_3,
                output_image)
            )

    def test_grayscale(self):
        three_channel = TEST_IMAGES['color-bluegray-1x1']

        source = FakeSource(three_channel.copy())

        hop = hoppers.HopperConvertToGrayscale(source)
        nt.assert_equal(hop.spec, ('grayscale', dict()))

        for output_image, meta_data in hop:
            nt.assert_true(np.array_equal(
                np.array([[207]]),
                output_image)
            )

    def test_threshold(self):
        source = FakeSource(TEST_IMAGES['grayscale-fourtone-2x2'])

        for thresh in range(60, 255, 64):
            hop = hoppers.HopperThreshold(source, thresh)
            nt.assert_equal(
                hop.spec,
                (
                    'threshold',
                    {
                        'thresh': thresh
                    }
                )
            )
            for output_image, meta_data in hop:
                compare_to = TEST_IMAGES['grayscale-fourtone-2x2']
                compare_to[compare_to > thresh] = 255
                compare_to[compare_to < 255] = 0
                print "COMPARE\n", compare_to
                print "OUTPUT\n", output_image
                nt.assert_true(
                    np.array_equal(
                        compare_to,
                        output_image
                    )
                )

    def test_invert(self):
        source = FakeSource(TEST_IMAGES['grayscale-blackfill-1x1'])

        hop = hoppers.HopperInvert(source)
        nt.assert_equal(hop.spec, ('invert', dict()))
        for output_image, meta_data in hop:
            nt.assert_true(np.array_equal(
                TEST_IMAGES['grayscale-whitefill-1x1'],
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
    for image, meta_data in source:
        print image


if __name__ == '__main__':
    main()
