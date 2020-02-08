import os
import unittest
from unittest import TestCase

import PIL
import numpy as np

import sys

sys.path.insert(0, '../digipath_mltk')
from toolkit import get_sample_selection_mask


class Test_get_sample_selection_mask(TestCase):

    def setUp(self) -> None:
        self.im_dir = os.path.abspath('../data/images')

    def test_get_sample_select_mask_otsu(self):

        # define the three image names and check their existence
        self.assertTrue(os.path.isdir(self.im_dir))
        sm_im_file = os.path.join(self.im_dir, 'CMU-1-small_im.tif')
        self.assertTrue(os.path.isfile(sm_im_file))
        otsu_mask_name = os.path.join(self.im_dir, 'threshold_otsu_mask.npy')
        self.assertTrue(os.path.isfile(otsu_mask_name))

        # open the three images
        small_im = PIL.Image.open(sm_im_file)
        mask_otsu = get_sample_selection_mask(small_im, 'threshold_otsu')
        otsu_mask_truth = np.load(otsu_mask_name)

        # compare the results size and sum of differences
        self.assertEqual(np.array(small_im.size).prod(), mask_otsu.size)
        self.assertEqual(otsu_mask_truth.size, mask_otsu.size)

        otsu_truth_array = np.array(otsu_mask_truth)
        otsu_array = np.array(mask_otsu)
        difference_sum = (otsu_truth_array != otsu_array).sum()

        self.assertEqual(difference_sum, 0)

    def test_get_sample_select_mask_rgb2lab(self):
        # define the three image names and check their existence
        self.assertTrue(os.path.isdir(self.im_dir))
        sm_im_file = os.path.join(self.im_dir, 'CMU-1-small_im.tif')
        self.assertTrue(os.path.isfile(sm_im_file))
        rgb2lab_mask_name = os.path.join(self.im_dir, 'threshold_rgb2lab_mask.npy')
        self.assertTrue(os.path.isfile(rgb2lab_mask_name))

        # open the three images
        small_im = PIL.Image.open(sm_im_file)
        mask_rgb2lab = get_sample_selection_mask(small_im, 'threshold_rgb2lab')
        rgb2lab_mask_truth = np.load(rgb2lab_mask_name)

        # compare the results size and sum of differences
        self.assertEqual(np.array(small_im.size).prod(), mask_rgb2lab.size)
        self.assertEqual(rgb2lab_mask_truth.size, mask_rgb2lab.size)

        rgb2lab_truth_array = np.array(rgb2lab_mask_truth)
        rgb2lab_array = np.array(mask_rgb2lab)
        difference_sum = (rgb2lab_truth_array != rgb2lab_array).sum()

        #                                           10/22/19 - This test is faileing for an unknown reason
        self.assertEqual(difference_sum, 0)


if __name__ == '__main__':
    unittest.main()
