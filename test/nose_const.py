#!/usr/bin/env python

"""
Some constants used by the nosetests.
"""

TEST_IMAGES = {
    'grayscale-blackfill-1x1': np.array([[0]],
                                        dtype=np.uint8),
    'grayscale-blackfill-3x3': np.array([[0, 0, 0],
                                         [0, 0, 0],
                                         [0, 0, 0]],
                                        dtype=np.uint8),
    'grayscale-whitefill-1x1': np.array([[255]],
                                        dtype=np.uint8),
    'grayscale-whitefill-3x3': np.array([[255, 255, 255],
                                         [255, 255, 255],
                                         [255, 255, 255]],
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
