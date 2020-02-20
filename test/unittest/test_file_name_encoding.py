import unittest
from unittest import TestCase

import sys

try:
    from digipath_mltk.toolkit import dict_to_patch_name, patch_name_to_dict
    print('using package installation of digipath_mltk ')
except:
    sys.path.insert(0, '../digipath_mltk')
    from toolkit import dict_to_patch_name, patch_name_to_dict
    pass


class Test_patch_name_encoding(TestCase):

    def setUp(self):
        self.file_1_name = 'd83cc7d1c94_100_340_dermis.jpg'
        self.file_1_dict = {'case_id': 'd83cc7d1c94',
                            'location_x': 100,
                            'location_y': 340,
                            'class_label': 'dermis',
                            'file_ext': '.jpg'}

        self.file_2_name = 'd83AA7d1c94_99_604_epidermis.jpg'
        self.file_2_dict = {'case_id': 'd83AA7d1c94',
                            'location_x': 99,
                            'location_y': 604,
                            'class_label': 'epidermis',
                            'file_ext': '.jpg'}

    def tearDown(self):
        del self.file_1_name
        del self.file_1_dict
        del self.file_2_name
        del self.file_2_dict

    def test_dict_to_patch_name(self):
        test_name = dict_to_patch_name(self.file_1_dict)
        self.assertEqual(test_name, self.file_1_name)
        test_name = dict_to_patch_name(self.file_2_dict)
        self.assertEqual(test_name, self.file_2_name)

    def test_patch_name_to_dict(self):
        test_dict = patch_name_to_dict(self.file_1_name)
        self.assertEqual(test_dict, self.file_1_dict)
        test_dict = patch_name_to_dict(self.file_2_name)
        self.assertEqual(test_dict, self.file_2_dict)


if __name__ == '__main__':
    unittest.main()

