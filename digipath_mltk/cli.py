# -*- coding: utf-8 -*-

"""Console script for dicom_wsi."""
import argparse
import logging
import sys

from digipath_mltk.toolkit import *


def parse_args():
    """Console script for DigiPath_MLTK."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--method",
                        dest='method',
                        default='wsi_to_patches_dir',
                        choices=['wsi_to_tfrecord',
                                 'tfrecord_to_masked_thumb',
                                 'wsi_to_patches_dir',
                                 'write_mask_preview_set',
                                 'registration_to_dir',
                                 'registration_to_tfrecord',
                                 'annotations_to_dir',
                                 'annotations_to_tfrecord'],
                        help="Method to run")

    parser.add_argument("-i", "--wsi_filename",
                        dest='wsi_filename',
                        required=True,
                        help="WSI File name")

    parser.add_argument("-f", "--wsi_floatname",
                        dest='wsi_floatname',
                        required=False,
                        help="offset WSI File name")

    parser.add_argument("-o", "--output_dir",
                        dest='output_dir',
                        default='.',
                        help="Where to write the images out")

    parser.add_argument("-c", "--class_label",
                        dest='class_label',
                        default='training_data',
                        help="label name fields for training")

    parser.add_argument("-d", "--thumbnail_divisor",
                        dest='thumbnail_divisor',
                        default=10,
                        help="Full size divisor to create thumbnail image")

    parser.add_argument("-S", "--pixel_hw",
                        dest='pixel_hw',
                        default=512,
                        help="Patch size")

    parser.add_argument("-P", "--patch_select_method",
                        dest='patch_select_method',
                        default='threshold_rgb2lab',
                        choices=['threshold_rgb2lab', 'threshold_otsu'],
                        help="Tissue detection method")

    parser.add_argument("-T", "--rgb2lab_threshold",
                        dest='rgb2lab_threshold',
                        default=80,
                        help="Detection threshold for rgb2lab detector")

    parser.add_argument("-e", "--image_level",
                        dest='image_level',
                        default=0,
                        help="Image zoom level")

    parser.add_argument("-l", "--file_ext",
                        dest='file_ext',
                        default='.png',
                        choices=['.png', '.jpg'],
                        help="Image format type")

    parser.add_argument("-t", "--threshold",
                        dest='threshold',
                        default=0,
                        help="Image detail & patch size dependent threshold")

    parser.add_argument("-s", "--patch_stride_fraction",
                        dest='patch_stride_fraction',
                        default=1.0,
                        help="Patch Stride [0-1]")

    parser.add_argument("-x", "--offset_x",
                        dest='offset_x',
                        default=0,
                        help="Begin at x position")

    parser.add_argument("-y", "--offset_y",
                        dest='offset_y',
                        default=0,
                        help="Begin at y position")

    parser.add_argument("-C", "--border_color",
                        dest='border_color',
                        default='blue',
                        help="Border color for mask previews")

    parser.add_argument("-V", "--verbose",
                        dest="logLevel",
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default="INFO",
                        help="Set the logging level")

    parser.add_argument("-r", "--tfrecord_file_name",
                        dest='tfrecord_file_name',
                        required=False,
                        help="TFRecord File name")

    parser.add_argument("-D", "--offset_data_file",
                        dest='offset_data_file',
                        required=False,
                        help="registration offset data file name")

    parser.add_argument("-a", "--xml_file_name",
                        dest='xml_file_name',
                        required=False,
                        help="xml annotations data file name")

    parser.add_argument("-L", "--csv_file_name",
                        dest='csv_file_name',
                        required=False,
                        help="annotations priority data file name")


    args = parser.parse_args()
    logging.basicConfig(stream=sys.stderr, level=args.logLevel,
                        format='%(name)s (%(levelname)s): %(message)s')

    logger = logging.getLogger(__name__)
    logger.setLevel(args.logLevel)

    run_parameters = dict()
    run_parameters['method'] = args.method
    run_parameters['wsi_filename'] = args.wsi_filename
    run_parameters['wsi_floatname'] = args.wsi_floatname
    run_parameters['output_dir'] = args.output_dir
    run_parameters['class_label'] = args.class_label
    run_parameters['thumbnail_divisor'] = int(args.thumbnail_divisor)
    run_parameters['patch_height'] = int(args.pixel_hw)
    run_parameters['patch_width'] = int(args.pixel_hw)
    run_parameters['patch_select_method'] = args.patch_select_method
    run_parameters['rgb2lab_threshold'] = int(args.rgb2lab_threshold)
    run_parameters['image_level'] = int(args.image_level)
    run_parameters['file_ext'] = args.file_ext
    run_parameters['threshold'] = int(args.threshold)
    run_parameters['patch_stride_fraction'] = float(args.patch_stride_fraction)
    run_parameters['offset_x'] = int(args.offset_x)
    run_parameters['offset_y'] = int(args.offset_y)
    run_parameters['border_color'] = args.border_color
    run_parameters['tfrecord_file_name'] = args.tfrecord_file_name
    run_parameters['offset_data_file'] = args.offset_data_file
    run_parameters['xml_file_name'] = args.xml_file_name
    run_parameters['csv_file_name'] = args.csv_file_name

    clean_run_parameters = dict()
    for k, v in run_parameters.items():
        if not v is None:
            clean_run_parameters[k] = v
            
    return clean_run_parameters


if __name__ == "__main__":
    run_parameters = parse_args()

    if run_parameters['method'] == 'wsi_to_tfrecord':
        wsi_file_to_patches_tfrecord(run_parameters)

    if run_parameters['method'] == 'tfrecord_to_masked_thumb':
        write_tfrecord_marked_thumbnail_image(run_parameters)

    if run_parameters['method'] == 'wsi_to_patches_dir':
        image_file_to_patches_directory_for_image_level(run_parameters)

    if run_parameters['method'] == 'write_mask_preview_set':
        write_mask_preview_set(run_parameters)

    if run_parameters['method'] == 'registration_to_dir':
        run_registration_pairs(run_parameters)

    if run_parameters['method'] == 'registration_to_tfrecord':
        run_registration_pairs(run_parameters)

    if run_parameters['method'] == 'annotations_to_dir':
        run_annotated_patches(run_parameters)

    if run_parameters['method'] == 'annotations_to_tfrecord':
        run_annotated_patches(run_parameters)
