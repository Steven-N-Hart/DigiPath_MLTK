import os
from tempfile import TemporaryDirectory
import unittest
from unittest import TestCase

import sys

try:
    from digipath_mltk.toolkit import get_run_parameters, get_run_directory_and_run_file
    print('using package installation of digipath_mltk ')
except:
    sys.path.insert(0, '../digipath_mltk')
    from toolkit import get_run_parameters, get_run_directory_and_run_file
    pass

class Test_run_pars(TestCase):

    def setUp(self):
        self.run_file = 'unit_test.yml'
        self.mock_dir = '/mock/directory/path'
        self.mock_file = 'whatta_notta_file.yml'

        self.test_str = ["# possible methods: image_2_tfrecord, tfrecord_2_masked_thumb",
                        "method:               image_2_tfrecord",
                        "image_file_name:      ../data/images/CMU-1-Small-Region.svs",
                        "output_dir:           ../../run_dir/results",
                        "patch_height:         224",
                        "patch_width:          224", "",
                        "# Options:            threshold_rgb2lab, threshold_otsu",
                        "patch_select_method:  threshold_rgb2lab", "",
                        "drop_threshold:       0.9",
                        "file_ext:             .jpg"]
        y_str = ''
        for s in self.test_str:
            y_str += s + '\n'
        self.yaml_str = y_str

        self.run_parameters = { 'method': 'image_2_tfrecord',
                                'image_file_name': '../data/images/CMU-1-Small-Region.svs',
                                'output_dir': '../../run_dir/results',
                                'patch_height': 224,
                                'patch_width': 224,
                                'patch_select_method': 'threshold_rgb2lab',
                                'drop_threshold': 0.9,
                                'file_ext': '.jpg'}

    def tearDown(self):
        del self.run_file
        del self.mock_dir
        del self.test_str
        del self.yaml_str
        del self.run_parameters


    def test_get_run_directory_and_run_file(self):
        sys.argv.append('-run_directory')
        sys.argv.append(self.mock_dir)
        sys.argv.append('-run_file')
        sys.argv.append(self.mock_file)

        run_directory, run_file = get_run_directory_and_run_file(sys.argv[1:])
        
        self.assertEqual(run_directory, self.mock_dir)
        self.assertEqual(run_file, self.mock_file)


    def test_run_parameters(self):
        run_directory = TemporaryDirectory()
        run_file = self.run_file
        fname = os.path.join(run_directory.name, run_file)

        with open(fname, 'w') as fh:
            print('%s' % (self.yaml_str), file=fh)

        run_parameters = get_run_parameters(run_directory.name, run_file)

        for k, v in self.run_parameters.items():
            self.assertEqual(v, run_parameters[k])

        self.assertEqual(run_directory.name, run_parameters['run_directory'])
        self.assertEqual(run_file, run_parameters['run_file'])

        run_directory.cleanup()


if __name__ == "__main__":
    unittest.main()
