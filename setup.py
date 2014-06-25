#!/usr/bin/env python

"""
The distutils setup.py file for FishFace.
"""

import distutils.core as duc

duc.setup(name='FishFace',
          version='2.0_pre',
          description="Finds the location and orientation over time "
                      "of a fish in a water flume.",
          url="https://github.com/wil-langford/FishFace2",
          py_modules=['fishface'],
          requires=['cv2 (>=2.4.8)', 'Pillow (>=2.4.0)', 'requests (>=2.3.0)']
)