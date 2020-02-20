import unittest
from unittest import TestCase
import numpy as np

import sys

try:
    from digipath_mltk.toolkit import get_fence_array
    print('using package installation of digipath_mltk ')
except:
    sys.path.insert(0, '../digipath_mltk')
    from toolkit import get_fence_array
    pass

class Test_fence_array_output(TestCase):

    def setUp(self):
        self.overall_length = 100
        self.patch_length = 10
        self.fence_array = np.array([   [ 0,  9], [10, 19], [20, 29], [30, 39], [40, 49],
                                        [50, 59], [60, 69], [70, 79], [80, 89], [90, 99] ] )

    def tearDown(self):
        del self.overall_length
        del self.patch_length
        del self.fence_array

    def test_get_fence_array(self):
        fence_array = get_fence_array(self.patch_length, self.overall_length)
        self.assertTrue((fence_array == self.fence_array).all())


if __name__ == '__main__':
    unittest.main()
