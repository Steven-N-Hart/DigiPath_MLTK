"""
digipath_toolkit.py

process large slide images using openslide
"""
import os
import tempfile
from collections import defaultdict, OrderedDict
import argparse

import numpy as np
import pandas as pd
import yaml

from skimage.filters import threshold_otsu
from skimage.color import rgb2lab

from PIL import Image
from PIL import ImageDraw
from PIL import TiffImagePlugin as tip

import tensorflow as tf
from tensorflow import io as tf_io

import openslide

MIN_STRIDE_PIXELS = 3
"""
                            parser utility: 
"""

def get_run_directory_and_run_file(args):
    """ Parse the input arguments to get the run_directory and run_file

    Args:
        system args:     -run_directory, -run_file (as below)

    Returns:
        run_directory:      where run_file is expected
        run_file:           yaml file with run parameters
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-run_directory', type=str)
    parser.add_argument('-run_file', type=str)
    args = parser.parse_args()

    run_directory = args.run_directory
    run_file = args.run_file

    return run_directory, run_file


def get_run_parameters(run_directory, run_file):
    """ Usage: run_parameters = get_run_parameters(run_directory, run_file)
        Read the input arguments into a dictionary
    Args:
        run_directory:      where run_file is expected
        run_file:           yaml file with run parameters

    Returns:
        run_parameters:     python dictionary of run parameters
    """
    run_file_name = os.path.join(run_directory, run_file)
    with open(run_file_name, 'r') as fh:
        run_parameters = yaml.safe_load(fh)
    run_parameters['run_directory'] = run_directory
    run_parameters['run_file'] = run_file

    return run_parameters

"""
                            notebook & development convenience
"""

def get_file_size_ordered_dict(data_dir, file_type_list):
    """ Usage:  file_size_ordered_dict = get_file_size_ordered_dict
        get size-ranked list of files of type in a directory

    Args:
        data_dir:           path to directory
        file_type_list:     file type extensions list (including period) e.g. = ['.svs', '.tif', '.tiff']

    Returns:
        ordered_dictionary: file_name: file_size   (ordered by file size)
    """
    file_size_ordered_dict = OrderedDict()
    if os.path.isdir(data_dir) == True:
        file_size_dict = {}
        for f in os.listdir(data_dir):
            ff = os.path.join(data_dir, f)
            if os.path.isfile(ff):
                _, f_ext = os.path.splitext(ff)
                if f_ext in file_type_list:
                    file_size_dict[f] = os.path.getsize(ff)

        file_size_dict_keys = list(file_size_dict.keys())
        sizes_idx = np.argsort(np.array(list(file_size_dict.values())))
        for idx in sizes_idx:
            k = file_size_dict_keys[idx]
            file_size_ordered_dict[k] = file_size_dict[k]
    else:
        file_size_ordered_dict['Directory Not Found: ' + data_dir] = 0

    return file_size_ordered_dict


def get_level_sizes_dict(image_file_name):
    """
    Usage:  level_sizes_dict = get_level_sizes_dict(image_file_name)
            read an openslide image type file to get the pyramid sizes available

    Args:
        image_file_name: full path or on path file name of .svs or some openslide format

    Returns:
        level_sizes_dict:
                            level_sizes_dict['image_size'] = os_obj.dimensions
                            level_sizes_dict['level_count'] = os_obj.level_count
                            level_sizes_dict["level_downsamples"] = os_obj.level_downsamples
                            level_sizes_dict['level_diminsions'] = os_obj.level_dimensions
    """
    level_sizes_dict = dict()
    os_obj = openslide.OpenSlide(image_file_name)
    level_sizes_dict['image_size'] = os_obj.dimensions
    level_sizes_dict['level_count'] = os_obj.level_count
    level_sizes_dict["level_downsamples"] = os_obj.level_downsamples
    level_sizes_dict['level_diminsions'] = os_obj.level_dimensions
    os_obj.close()

    return level_sizes_dict


def lineprint_level_sizes_dict(image_file_name):
    """
    Usage:  lineprint_level_sizes_dict(image_file_name)
            display the openslide image type file pyramid sizes available

    Args:
        image_file_name: full path or on path file name of .svs or some openslide format

    Returns:
        None:               (prints)
                            'image_size': os_obj.dimensions
                            'level_count': os_obj.level_count
                            'level_downsamples': os_obj.level_downsamples
                            'level_diminsions': os_obj.level_dimensions
    """
    level_sizes_dict = get_level_sizes_dict(image_file_name)
    key_list = ['image_size', 'level_count', 'level_diminsions', 'level_downsamples']
    print(' ')
    for k in key_list:
        if k in level_sizes_dict:
            print('%20s: ' % (k), level_sizes_dict[k])
        else:
            print('%20s: not found' % (k))
    print(' ')


"""
                            patch wrangling
"""

def dict_to_patch_name(patch_image_name_dict):
    """ Usage: patch_name = dict_to_patch_name(patch_image_name_dict)
        convert the dictionary into a file name string
    
    Args:
        patch_image_name_dict:  {'case_id': 'd83cc7d1c94', 
                                 'location_x': 100, 
                                 'location_y': 340, 
                                 'class_label': 'dermis', 
                                 'file_type': '.jpg' }
        
    Returns:
        patch_name:     file name (without directory path)
    """

    if len(patch_image_name_dict['file_ext']) > 1 and patch_image_name_dict['file_ext'][0] != '.':
        patch_image_name_dict['file_ext'] = '.' + patch_image_name_dict['file_ext']

    patch_name = patch_image_name_dict['case_id']
    patch_name += '_%i'%patch_image_name_dict['location_x']
    patch_name += '_%i'%patch_image_name_dict['location_y'] 
    patch_name += '_%s'%patch_image_name_dict['class_label']
    patch_name += '%s'%patch_image_name_dict['file_ext']
    
    return patch_name


def patch_name_to_dict(patch_file_name):
    """ Usage: patch_image_name_dict = patch_name_to_dict(patch_file_name)
        convert a file name string into a dictionary

    Args:
        fname:          file name as created by get_patch_name()
        
    Returns:
        patch_image_name_dict:  {'case_id': field[0], 
                                 'location_x': int(field[1]), 
                                 'location_y': int(field[2]), 
                                 'class_label': field[3], 
                                 'file_ext': '.' + field[4] }
    """
    name_part, file_ext = os.path.splitext(patch_file_name)
    if len(file_ext) > 0 and file_ext[0] == '.':
        file_ext = file_ext[1:]

    name_field_list = name_part.split('_')

    patch_image_name_dict = {'case_id': name_field_list[0], 
                             'location_x': int(name_field_list[1]), 
                             'location_y': int(name_field_list[2]), 
                             'class_label': name_field_list[3], 
                             'file_ext': '.' + file_ext}
    
    return patch_image_name_dict


def check_patch_in_bounds(x, y, X_dim, Y_dim):
    """ Usage: TrueFalse = check_patch_in_bounds(x, y, X_dim, Y_dim)
                determine if the box is within the image
    Args:
        x:               a tuple, list or array (x_start, x_end)
        y:               a tuple, list or array (y_start, Y_end)
        X_dim:           a tuple, list or array (Image_X_start, Image_X_end)
        Y_dim:           a tuple, list or array (Image_Y_start, Image_Y_end)
    """
    if x[0] > x[1] or y[0] > y[1] or X_dim[0] > X_dim[1] or Y_dim[0] > Y_dim[1]:
        return False

    if x[0] >= X_dim[0] and y[0] >= Y_dim[0] and x[1] < X_dim[1] and y[1] < Y_dim[1]:
        return True

    else:
        return False


def im_pair_hori(im_0, im_1):
    """ Usage: new_im = im_pair_hori(im_0, im_1)
            combine a list of PIL images horizontaly
    """
    w0 = im_0.size[0]
    w = w0 + im_1.size[0]
    h = max(im_0.size[1], im_1.size[1])

    new_im = tip.Image.new('RGB', (w, h))
    box = (0, 0, w0, h)
    new_im.paste(im_0, box)

    box = (w0, 0, w, h)
    new_im.paste(im_1, box)

    return new_im

def get_fence_array(patch_length, overall_length):
    """ See New Function: fence_array = get_strided_fence_array(patch_len, patch_stride, arr_start, arr_end)

        Usage: fence_array = get_fence_array(patch_length, overall_length)
        create a left-right set of pairs that descrete overall_length into patch_length segments

    Args:
        patch_length:   patch size - number of pixels high or wide
        patch_length:   overall number of pixels high or wide

    Returns:
        fence_array:    boundry values for each segment
        -----------:    [[left_0, right_0],
                         [left_1, right_1],
                         [left_2, right_2],... ]
    """
    # Determine the array size
    n_fenced = overall_length // patch_length  # number of boxes
    n_remain = 1 + overall_length % patch_length  # number of pixels leftover
    paddit = n_remain // 2  # padding for the beginning

    if n_remain == patch_length:  # exact fit special case: exactly one left over
        paddit = 0
        n_fenced = n_fenced + 1

    # Allocate as integers for use as indices
    fence_array = np.zeros((n_fenced, 2)).astype(int)
    for k in range(n_fenced):
        # for each box edge, get the beginning and end pixel location
        if k == 0:
            # first case special (padding)
            fence_array[k, 0] = paddit
            # add the width to it
            fence_array[k, 1] = fence_array[k, 0] + patch_length - 1

        elif fence_array[k - 1, 1] + patch_length <= overall_length:
            # Previous right pixel plus one
            fence_array[k, 0] = fence_array[k - 1, 1] + 1
            # add the width to it
            fence_array[k, 1] = fence_array[k, 0] + patch_length - 1

    return fence_array


def get_sample_selection_mask(small_im, patch_select_method, run_parameters=None):
    """ Usage: mask_im = get_sample_selection_mask(small_im, patch_select_method)

    Args:
        small_im:               selection image
        patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'

    Returns:
        mask_im:                numpy boolean matrix size of small_im

    """
    if not run_parameters is None and 'rgb2lab_threshold' in run_parameters:
        rgb2lab_threshold = run_parameters['rgb2lab_threshold']
    else:
        rgb2lab_threshold = 80
    #                   initialize the return value
    mask_im = None

    if patch_select_method == 'threshold_rgb2lab':
        thresh = rgb2lab_threshold
        np_img = np.array(small_im.convert('RGB'))
        np_img = rgb2lab(np_img)
        np_img = np_img[:, :, 0]
        mask_im = np.array(np_img) < thresh

    elif patch_select_method == 'threshold_otsu':
        grey_thumbnail = np.array(small_im.convert('L'))
        thresh = threshold_otsu(grey_thumbnail)
        mask_im = np.array(grey_thumbnail) < thresh

    else:
        print('patch_select_method %s not implemented' % (patch_select_method))

    return mask_im


def get_offset_array_start_and_end(array_length, array_offset, arry_2_lngth=None):
    """ Usage:  array_start, array_end = get_offset_array_start_and_end(array_length, array_offset, arry_2_lngth)
                single axis boundry in context of offset

    Args:
        array_length:   image dimension         (positive integer)
        array_offset:   registration offset     (signed integer)
        arry_2_lngth:   length of the second array (positive integer)

    Returns:            (positive integers)
        array_start:    first index in image diminsion
        array_end:      last index + 1 in image diminsion
    """
    array_start = max(0, array_offset)
    if arry_2_lngth is None:
        array_end = min(array_length, array_length + array_offset)
    else:
        array_end = min(array_length, arry_2_lngth + array_start)

    return array_start, array_end


def get_strided_fence_array(patch_len, patch_stride, arr_start, arr_end):
    """ Usage:   sf_array = get_strided_fence_array(patch_len, patch_stride, arr_start, arr_end)
                            pairs of bounds for one dimension of a patch array
                            single axis, strided: first, last patch location array

    Args:               (positive integers)
        patch_len:      patch length, patch dimension
        patch_stride:   percent of patch dimension - stride = floor(patch_len * patch_stride)
        arr_start:      array start index, beginning index using closed zero-based indexing
        arr_end:        array end index, last index using CLOSED zero-based indexing (0, arr_end]

    Returns:
        fence_array:    numpy 2 d array like [[p_start, p_end], [p_start, p_end],...]

    """
    #                   fence stride is the distance between starting points
    fence_stride = max(int(np.abs(patch_len * patch_stride)), 1)

    #                   pre-allocate a max number-of-patches by 2 numpy array
    array_size = (np.abs(arr_end - arr_start) / fence_stride).astype(np.int)
    fence_array = np.zeros((array_size, 2)).astype(np.int)

    #                   initialize the first location and a fence_array index
    p_loc = np.array([arr_start, arr_start + patch_len]).astype(np.int)
    pair_number = 0

    #                   walk toward the end
    while p_loc[1] < arr_end:
        #               add this location pair to the fence array
        fence_array[pair_number, :] = p_loc
        pair_number += 1

        #               advance the next pair
        p_loc[0] = p_loc[0] + fence_stride
        p_loc[1] = p_loc[0] + patch_len

    #                   cover the short ending case
    if pair_number < fence_array.shape[0]:
        fence_array = fence_array[0:pair_number + 1, :]

    return fence_array


def get_strided_patches_dict_for_image_level(run_parameters):
    """ Usage: strided_patches_dict = get_strided_patches_dict_for_image_level(run_parameters)
    Args:

    Returns:

    """
    wsi_filename = run_parameters['wsi_filename']
    thumbnail_divisor = run_parameters['thumbnail_divisor']
    patch_height = run_parameters['patch_height']
    patch_width = run_parameters['patch_width']

    #                   set defaults for newly added parameters
    if 'image_level' in run_parameters:
        image_level = run_parameters['image_level']
    else:
        image_level = 0

    if 'offset_x' in run_parameters:
        offset_x = run_parameters['offset_x']
    else:
        offset_x = 0

    if 'offset_y' in run_parameters:
        offset_y = run_parameters['offset_y']
    else:
        offset_y = 0

    if 'patch_stride_fraction' in run_parameters:
        patch_stride = run_parameters['patch_stride_fraction']
    else:
        patch_stride = 1.0

    if 'wsi_floatname' in run_parameters and not run_parameters['wsi_floatname'] is None:
        os_im_2_obj = openslide.OpenSlide(run_parameters['wsi_floatname'])
        arry_2_x_lngth, arry_2_y_lngth = os_im_2_obj.level_dimensions[image_level]
        os_im_2_obj.close()
    else:
        arry_2_x_lngth = None
        arry_2_y_lngth = None

    #       assure minimum stride s.t. arrays advance by at least MIN_STRIDE_PIXELS
    patch_stride = max(patch_stride, (MIN_STRIDE_PIXELS / min(patch_width, patch_height) ) )

    #                     OpenSlide Open                      #
    os_im_obj = openslide.OpenSlide(wsi_filename)

    #       guard image level off by one
    image_level = min(image_level, os_im_obj.level_count - 1)

    obj_level_diminsions = os_im_obj.level_dimensions
    obj_level_downsample = os_im_obj.level_downsamples[image_level]

    #       adjust offset to this scale for location arrays start - end
    offset_y = int(offset_y / obj_level_downsample)
    offset_x = int(offset_x / obj_level_downsample)

    #       get the start, stop locations list for the rows     -- Scaled to image_level
    pixels_height = obj_level_diminsions[image_level][1]
    row_start, row_end = get_offset_array_start_and_end(pixels_height, offset_y, arry_2_y_lngth)
    rows_fence_array = get_strided_fence_array(patch_height, patch_stride, row_start, row_end)

    #       get the start, stop locations list for the columns  -- Scaled to image_level
    pixels_width = obj_level_diminsions[image_level][0]
    col_start, col_end = get_offset_array_start_and_end(pixels_width, offset_x, arry_2_x_lngth)
    cols_fence_array = get_strided_fence_array(patch_width, patch_stride, col_start, col_end)

    #       get a thumbnail image for the patch select method   -- Scaled to image_level / thumbnail_divisor
    thumbnail_size = (int(pixels_width // thumbnail_divisor),
                      int(pixels_height // thumbnail_divisor))

    #       thumb scale on full size image
    small_im = os_im_obj.get_thumbnail(thumbnail_size)
    os_im_obj.close()
    #                     OpenSlide Close                      #

    #       package the return dictionary
    strided_patches_dict = {'small_im': small_im,
                            'cols_fence_array': cols_fence_array,
                            'rows_fence_array': rows_fence_array,
                            'thumbnail_divisor': thumbnail_divisor}

    return strided_patches_dict

def get_patch_location_array_for_image_level(run_parameters):
    """ Usage: patch_location_array = get_patch_location_array_for_image_level(run_parameters)
        using 'patch_select_method", find all upper left corner locations of patches
        that won't exceed image size givin the 'patch_height' and 'patch_width'

    Args (run_parameters):  python dict.keys()
                                wsi_filename:           file name (with valid path)
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
                                threshold:              minimimum sum of thresholded image (default = 0)
                                image_level:            openslide image pyramid level 0,1,2,...
    Returns:
        patch_location_array:   [[x, y], [x, y],... ]   n_pairs x 2 numpy array

    """
    #                   initialize an empty return value
    patch_location_array = []
    #                   name the input variables
    patch_select_method = run_parameters['patch_select_method']

    #                   set defaults for newly added parameters
    if 'threshold' in run_parameters:
        threshold = run_parameters['threshold']
    else:
        threshold = 0

    #                   full scale patch locations for the selection image & thumbnail_divisor scale
    strided_patches_dict = get_strided_patches_dict_for_image_level(run_parameters)
    small_im = strided_patches_dict['small_im']
    cols_fence_array = strided_patches_dict['cols_fence_array']
    rows_fence_array = strided_patches_dict['rows_fence_array']
    thumbnail_divisor = strided_patches_dict['thumbnail_divisor']

    #                   get the binary mask as a measure of image region content
    mask_im = get_sample_selection_mask(small_im, patch_select_method).astype(np.int)

    #                                       zip & rescale Fence Arrays to mask image size
    #                   iterator for rows:  (top_row, bottom_row, full_scale_row_number)
    it_rows = zip(rows_fence_array[:, 0] // thumbnail_divisor,
                  rows_fence_array[:, 1] // thumbnail_divisor,
                  rows_fence_array[:, 0])

    #                   loop variables for iterator for cols
    lft_cols = cols_fence_array[:, 0] // thumbnail_divisor
    rgt_cols = cols_fence_array[:, 1] // thumbnail_divisor
    cols_array = cols_fence_array[:, 0]

    for tmb_row_top, tmb_row_bot, row_n in it_rows:
        #               iterator for cols:  (left_column, right_column, full_scale_column_number)
        it_cols = zip(lft_cols, rgt_cols, cols_array)

        for tmb_col_lft, tmb_col_rgt, col_n in it_cols:

            #           select this patch if the selected patch pixels add to more than threshold (default = 0)
            if (mask_im[tmb_row_top:tmb_row_bot, tmb_col_lft:tmb_col_rgt]).sum() > threshold:

                #       add the image level scale row and column of the upper left corner to the list
                patch_location_array.append((col_n, row_n))

    #                   patch locations at image_level scale   [(x, y), (x, y),...]     -- Scaled to image_level
    return patch_location_array

"""
                            patch image generators
"""

class PatchImageGenerator():
    """
    General case patch image generator for openslide Whole Slide Image file types

    Usage:  patch_image_generator = PatchImageGenerator(run_parameters)
            try:
                patch_dict = patch_image_generator.next_patch()
            execpt StopIteration:
                # catch StopIterationError - no action required except pass
                pass

    Args:
        run_parameters:         (with these keys)
                                wsi_filename:           file name (with valid path)
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
                                threshold:              minimimum sum of thresholded image (default = 0)
                                image_level:            openslide pyramid images level
    yields:
        patch_dict:             (with these keys)
                                patch_image:            PIL image of patch size
                                image_level_x:          column location in image level image
                                image_level_y:          row location in image level image
                                level_0_x:              column location in image (level 0)
                                level_0_y:              row location in image (level 0)
    """

    def __init__(self, run_parameters):
        #                       image_level_loc_array  = [(row, col), (row, col),...]     -- Scaled to image_level
        self.image_level_loc_array = get_patch_location_array_for_image_level(run_parameters)

        #                       image_level determines scale, patch width and height are fixed
        self.image_level = run_parameters['image_level']
        self.patch_size = (run_parameters['patch_width'], run_parameters['patch_height'])

        #                       assign inputs, Open the file
        self.os_obj = openslide.OpenSlide(run_parameters['wsi_filename'])

        #                       get the scale multiplier
        _multi_ = self.os_obj.level_downsamples[self.image_level]

        #                       rescale to image full size :
        self.level_0_location_array = [(int(p[0] * _multi_), int(p[1] * _multi_)) for p in self.image_level_loc_array]

        #                       size of the iteration and initialize for +1 opening index of 0
        self._number_of_patches = len(self.image_level_loc_array)
        self._patch_number = -1

    def __del__(self):
        #                       just before exit, Close the file
        self.os_obj.close()

    def next_patch(self):

        #                       initialized to -1, opens as 0 ends as number of patches -1 (as zero-indexing should)
        self._patch_number += 1

        #                       ( for every patch )
        if self._patch_number < self._number_of_patches:

            #                   iteration number
            patch_dict = {'patch_number': self._patch_number}

            #                   insert the next image_level scaled x and y into the return dictionary
            patch_dict['image_level_x'] = self.image_level_loc_array[self._patch_number][0]
            patch_dict['image_level_y'] = self.image_level_loc_array[self._patch_number][1]

            #                   insert the full scale location x, y in return dict and the location tuple
            patch_dict['level_0_x'] = self.level_0_location_array[self._patch_number][0]
            patch_dict['level_0_y'] = self.level_0_location_array[self._patch_number][1]
            location = (patch_dict['level_0_x'], patch_dict['level_0_y'])

            #                   read the patch_sized image at the loaction and insert it in the return dict
            patch_dict['patch_image'] = self.os_obj.read_region(location, self.image_level, self.patch_size)

            return patch_dict

        else:
            #                   This is standard practice for python generators -
            raise StopIteration()

""" Input conditioning """


def patch_name_parts_limit(name_str, space_replacer=None):
    """ Usage:  par_name = patch_name_parts_limit(name_str, <space_replacer>)
                clean up name_str such that it may be decoded with
                patch_name_to_dict and serve as a valid file name
    Args:
        name_str:       string representation for case_id or class_label or file_extension
        space_replacer: python str to replace spaces -

    Returns:
        part_name:      name_str string with spaces removed, reserved characters removed
                        and underscores replaced with hyphens
    """
    # remove spaces: substitute if valid space replacer is input
    if space_replacer is not None and isinstance(space_replacer, str):
        name_str = name_str.replace(' ', space_replacer)

    # no spaces!
    name_str = name_str.replace(' ', '')

    # remove reserved characters
    reserved_chars = ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']
    part_name = ''.join(c for c in name_str if not c in reserved_chars)

    # replace underscore with hyphen to allow decoding of x and y location
    part_name = part_name.replace('_', '-')

    return part_name


def patch_name_parts_clean_with_warning(file_name_base, class_label, show_warnings=False):
    """ Usage:  name_base_clean, class_label_clean = patch_name_parts_clean_with_warning(name_base, class_label)
                sanitize case_id, class_label and file_ext so that they may be decoded
                - warn user that input parameter changed
    Args:
        file_name_base:     file name string
        class_label:        class_id

    Retruns:
        name_base_clean:    file_name_base with reserved_chars removed
        class_label_clean:  class_label with reserved_chars removed

    Warnings:               (if names are changed)
        UserWarning:        Input parameter changed

    """
    par_change_warning = 'Input parameter changed.\t(for name readback decoding)'
    warn_format_str = '\n%s\nparameter:\t%s\nchanged to:\t%s\n'

    name_base_clean = patch_name_parts_limit(file_name_base.strip())
    if show_warnings == True and name_base_clean != file_name_base:
        print(((warn_format_str) % (par_change_warning, file_name_base, name_base_clean)))

    class_label_clean = patch_name_parts_limit(class_label.strip())
    if show_warnings == True and class_label_clean != class_label:
        print(((warn_format_str) % (par_change_warning, file_name_base, name_base_clean)))

    return name_base_clean, class_label_clean


"""                         Use Case 1 

        Givin a WSI (Whole Slide Image) and a label, export patches into TFRecords or Folders (raw images).
        
        
"""

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))


def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def tf_imp_dict(image_string, label, image_name, class_label='class_label'):
    """ tf_image_patch_dict = tf_imp_dict(image_string, label, image_name='patch')
        Create a dictionary of jpg image features

    Args:
        image_string:  bytes(PIL_image)
        label:         sequence number     (this is not the label you are looking for)
        image_name:    bytes(image_name)   (this is the label)

    Returns:
        one_tf_train_example: tf.train.Example

    """
    image_shape = tf.image.decode_jpeg(image_string).shape
    feature = {'height': _int64_feature(image_shape[0]),
               'width': _int64_feature(image_shape[1]),
               'depth': _int64_feature(image_shape[2]),
               'label': _int64_feature(label),
               'class_label': _bytes_feature(class_label),
               'image_name': _bytes_feature(image_name),
               'image_raw': _bytes_feature(image_string)}

    return tf.train.Example(features=tf.train.Features(feature=feature))


def _parse_tf_imp_dict(example_proto):
    """ tf_image_patch_dict = _parse_tf_imp_dict(example_proto)
        readback dict for tf_imp_dict() (.tfrecords file decoder)

    Args:
        example_proto:

    Returns:
        iterable_tfrecord:   try iterable_tfrecord.__iter__()
    """
    image_feature_description = {
        'height': tf.io.FixedLenFeature([], tf.int64),
        'width': tf.io.FixedLenFeature([], tf.int64),
        'depth': tf.io.FixedLenFeature([], tf.int64),
        'label': tf.io.FixedLenFeature([], tf.int64),
        'class_label': tf.io.FixedLenFeature([], tf.string),
        'image_name': tf.io.FixedLenFeature([], tf.string),
        'image_raw': tf.io.FixedLenFeature([], tf.string)}

    return tf.io.parse_single_example(example_proto, image_feature_description)


def get_iterable_tfrecord(tfr_name):
    """ usage:
    iterable_tfrecord = get_iterable_tfrecord(tfr_name)

    Args:
        tfr_name:   tensorflow data TFRecord file

    Returns:
        iterable_tfrecord:  an iterable TFRecordDataset mapped to _parse_tf_imp_dict
    """
    return tf.data.TFRecordDataset(tfr_name).map(_parse_tf_imp_dict)


def wsi_file_to_patches_tfrecord(run_parameters):
    """ Usage: tfrecord_file_name = wsi_file_to_patches_tfrecord(run_parameters)
    Args:
        run_parameters:         with keys:
                                    output_dir
                                    wsi_filename
                                    class_label
                                    patch_height
                                    patch_width
                                    thumbnail_divisor
                                    patch_select_method
                                    threshold
                                    image_level

                                (optional)
                                    file_ext
    Returns:
        None:                    prints number of images and output file name if successful

    """
    _, file_name_base = os.path.split(run_parameters['wsi_filename'])
    file_name_base, _ = os.path.splitext(file_name_base)
    class_label = run_parameters['class_label']
    output_dir = run_parameters['output_dir']

    if 'file_ext' in run_parameters:
        file_ext = run_parameters['file_ext']
    else:
        file_ext = ''

    if os.path.isdir(output_dir) == False:
        os.makedirs(output_dir)
        print('created new dir:', output_dir)

    tfrecord_file_name = file_name_base + '.tfrecords'
    tfrecord_file_name = os.path.join(output_dir, tfrecord_file_name)

    # sanitize case_id, class_label and file_ext so that they may be decoded - warns user if input parameter changed
    file_name_base, class_label = patch_name_parts_clean_with_warning(file_name_base, class_label)
    patch_image_name_dict = {'case_id': file_name_base, 'class_label': class_label, 'file_ext': file_ext}

    patch_generator = PatchImageGenerator(run_parameters)

    with tf_io.TFRecordWriter(tfrecord_file_name) as writer:
        seq_number = 0
        while True:
            try:
                patch_dict = patch_generator.next_patch()
                x = patch_dict['image_level_x']
                y = patch_dict['image_level_y']
                patch_image_name_dict['location_x'] = x
                patch_image_name_dict['location_y'] = y
                patch_name = dict_to_patch_name(patch_image_name_dict)

                image_string = patch_dict['patch_image'].convert('RGB')

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                try:
                    image_string.save(tmp.name)
                    image_string = open(tmp.name, 'rb').read()

                except:
                    print('Image write-read exception with patch # %i, named:\n%s' % (seq_number, patch_name))
                    pass

                finally:
                    os.unlink(tmp.name)
                    tmp.close()

                tf_example_obj = tf_imp_dict(image_string,
                                             label=seq_number,
                                             image_name=bytes(patch_name, 'utf8'),
                                             class_label=bytes(class_label, 'utf8'))

                writer.write(tf_example_obj.SerializeToString())
                seq_number += 1

            except StopIteration:
                print('%5i images written to %s' % (seq_number, tfrecord_file_name))
                break

    return tfrecord_file_name


def run_imfile_to_tfrecord(run_parameters):
    """ read the run_parameters dictionary & execute function: svs_file_to_patches_tfrecord with those

    Args:
        run_parameters:     with keys:
                                wsi_filename:           file name (with valid path)
                                output_dir:             writeable directory for the tfrecord
                                class_label:            label for all images
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                file_ext:               default is '.jpg' ('.png') was also tested
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
                                threshold:              minimimum sum of thresholded image (default = 0)

    Returns:
        (writes tfrecord file - prints filename if successful)

    """
    tfrecord_file_name = wsi_file_to_patches_tfrecord(run_parameters)
    if os.path.isfile(tfrecord_file_name):
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(tfrecord_file_name)
        if size > 0:
            print('TFRecord file size:%i\n%s\n'%(size, tfrecord_file_name))

"""                             Use Case 2

        Givin a WSI (Whole Slide Image) and an Annotation File, export patches into TFRecords.
        
        1.  Annotation File must follow QuPath Annotation convention
        2.  Requires dictionary for class labels 
"""

def get_priority_ordered_labels(label_id_priority_fname):
    """ ordered_priority_dict = get_priority_ordered_labels(label_id_priority_fname)
    read the input .csv file into a priority dictionary struct

    Args:
        label_id_priority_fname:    with Header = Label, ID, Priority

    Returns:
        ordered_priority_dict:      {priority_number: {'label': label_str, 'ID': str_number}}
                                    sorted with largest priority number first
    """
    # create the ordered_priority_dict for return, and a id_priority reverse dict 4 lookups
    priority_tuples_list = []

    # read the file
    lines = ''
    try:
        with open(label_id_priority_fname, 'r') as fh:
            lines = fh.readlines()
    except:
        print('failed opening: ', label_id_priority_fname)
        lines = ''
        pass

    # read the .csv lines into the dict   Header = Label, ID, Priority
    if len(lines) > 0:
        for line in lines:
            ln_list = line.strip().split(',')
            if len(ln_list) > 1 and ln_list[0] != 'Label':
                #                   Fix name clash: .xml "Id" vs .csv "ID" - Renaming csv-ID as label_ID
                # tuple:                    (    priority,     {label: label_name,     ID: ID_number}    )
                priority_tuples_list.append((int(ln_list[2]), {'label': ln_list[0], 'label_ID': ln_list[1]}))

    return OrderedDict(sorted(priority_tuples_list, reverse=True))


def get_ordered_priority_label_coords_dict(xml_file_name, label_id_priority_fname):
    """ Usage:
    priority_dict = get_ordered_priority_label_coords_dict(xml_file_name, label_id_priority_fname)
    parse an xml file for key fields needed for annotation selection of images

    Args:
        xml_file_name:              QuPath Annotation convention xml file
        label_id_priority_fname:    with columns Label, Id, Priority

    Returns:
        priority_dict:              python dict of dicts - with priority numbers as ordered keys,
                                        values are python dicts with:
                                            label:  Text
                                            Text:   label
                                            coords: vertices as numpy (n x 2) array [[x, y], [x, y],...]
                                            ID:     region Id number - depreciated - defined by label

    """
    # define which region keys to include
    REGION_KEYS = {'Id': 'int', 'Text': 'str', }
    # REGION_KEYS =  {'Id': 'int', 'Text': 'str', 'Zoom': 'float', 'Analyze': 'bool'}
    INT_BOOL_DICT = {1: True, 0: False}

    # module call:          get the {priority: {label: l, ID: n}
    ordered_priority_dict = get_priority_ordered_labels(label_id_priority_fname)

    # read the file into text
    with open(xml_file_name, 'r') as fh:
        lines = fh.readlines()

    if len(lines) == 0 or ordered_priority_dict is None:
        print('\n\n\t\t\tThrow_A_Pythonic_Conniption_Fit')
        print('\t\t\tFail to read: ', xml_file_name, '\n\n')
        return ordered_priority_dict

    # create the reverse dict  { label:    priority}
    label_ID_Priority_dict = {v['label']: k for k, v in ordered_priority_dict.items()}

    # initialize region-vertex loop region-coords loop cycle variables
    reg_on = False
    v_on = False
    vertex_list = []
    region_dict = {}

    for line in lines:
        # region-vertex loop: skip to bottom of loop first, work back up as conditions found
        #       finds "Region", fills in keys, moves up-loop,
        #       finds "Vertex" collects all "Vertex" tags,
        #       takes this first if ... when end of Vertices is found
        #       fills "priority" defined .csv (reverse dict label_ID_Priority_dict)
        if reg_on == True and v_on == True and line.strip() == '</Vertices>':

            # end of region - add region_dict to ordered_priority_dict if coords found
            if 'Text' in region_dict and region_dict['Text'] in label_ID_Priority_dict and len(vertex_list) > 1:
                # priority - .csv reverse dict {label: priority} with label=="Text" found in xml
                priority = label_ID_Priority_dict[region_dict['Text']]
                for k in REGION_KEYS.keys():
                    if k in region_dict:
                        ordered_priority_dict[priority][k] = region_dict[k]
                ordered_priority_dict[priority]['vertices'] = np.array(vertex_list)

            else:
                #                                                       Throw Warning | Error Here?
                print('\n\n\t\t\tThrow_A_Pythonic_Conniption_Fit')
                print('\nlen(vertex_list)', len(vertex_list), '\nregion_dict\n', region_dict, '\n\n')

            # restart region-vertex loop: reset all region-coords loop cycle variables
            reg_on = False
            v_on = False
            vertex_list = []
            region_dict = {}

        elif reg_on == True and v_on == True and '<Vertex' in line.strip()[0:7]:
            # append every <vertex> in <Vertices> to the list of coords

            # remove the xml markup and split on empty space, find & insert the X=..., Y=... elements
            vertex_line_list = line.strip().strip('<').strip('>').strip('/').split()  # .split(' ')
            xy_dict = {}
            # find
            for v in vertex_line_list:
                if v[0] == 'X':
                    kv_pair = v.split('=')
                    xy_dict['X'] = float(kv_pair[1].strip('"'))

                elif v[0] == 'Y':
                    kv_pair = v.split('=')
                    xy_dict['Y'] = float(kv_pair[1].strip('"'))

            # insert in vertex list
            if 'X' in xy_dict and 'Y' in xy_dict:
                vertex_list.append([xy_dict['X'], xy_dict['Y']])

        if reg_on == True and '<Vertices' in line:
            # set to begin parsing Vertex lines
            v_on = True

        if reg_on == False and '<Region ' in line.strip()[0:8]:
            #                       begin parsing the new region
            reg_on = True
            v_on = False  # (with paranoia)
            region_dict = {}

            # parse this line ( <Region ) to get find key-value pairs named in REGION_KEYS
            region_list = line.strip().split()
            for reg_item in region_list:
                if '=' in reg_item:
                    # split into a key-value pair
                    item_list = reg_item.strip().split('=')
                    if len(item_list) == 2:
                        for k in REGION_KEYS:
                            # insert key-value pair if key is defined above in REGION_KEYS
                            if k in item_list[0][0:len(k)]:
                                if REGION_KEYS[k] == 'int':
                                    region_dict[k] = int(item_list[1].strip('"'))
                                elif REGION_KEYS[k] == 'float':
                                    region_dict[k] = float(item_list[1].strip('"'))
                                elif REGION_KEYS[k] == 'bool':
                                    region_dict[k] = INT_BOOL_DICT[int(item_list[1].strip('"'))]
                                else:
                                    region_dict[k] = item_list[1].strip('"')

    return ordered_priority_dict


def get_select_bounds_from_mask(mask_mat, xy):
    """ Usage: start_stop_dict = get_select_bounds_from_mask(mask_mat, xy='x')
    find the first and last unmasked row (y) or col (x) in the mask image input mask_mat

    Args:
        mask_mat:           2d numpy binary array
        xy:                 character x for x axis or y for y axis

    Returns:
        start_stop_dict:    {xy+'_start': _start_, xy+'_end': _stop_}

    """
    # initialize
    _start_ = None
    _stop_ = None

    # translate input variables
    if xy == 'x':
        axis = 1

    elif xy == 'y':
        axis = 0

    # sum of axis: sum_of_rows is x, axis=1,
    sum_of_axis = mask_mat.sum(axis=axis)
    current_greater_than = 0
    for k in range(sum_of_axis.size):
        if sum_of_axis[k] > 0:
            current_greater_than = k
            if _start_ is None:
                _start_ = k

    # set the last row if a first row one more were found to contain ones
    if not _start_ is None and current_greater_than > _start_:
        _stop_ = current_greater_than

    # cover the all the way to the include all cases
    if _start_ is None:
        _start_ = 0

    if _stop_ is None:
        _stop_ = sum_of_axis.shape[0]  # k

    return _start_, _stop_


def get_region_mask(region_coords, thumbnail_divisor, thumbnail_size):  # image_dimensions):
    """ mask_im, img = get_region_mask(region_coords, thumbnail_divisor,image_dimensions)
    fabricate a numpy array image mask for thumbnail size with region coords (vertices)
    Args:
    Returns:
    """
    # scale the region coords tuple with the thumbnail_divisor as type int
    xy_list = (region_coords / thumbnail_divisor).astype(np.int).tolist()
    xy_list = [(p[1], p[0]) for p in xy_list]

    img = Image.fromarray(np.zeros((thumbnail_size[1], thumbnail_size[0])).astype(np.uint8))

    # make it a Pillow Draw and draw the polygon from the list of (x,y) tuples
    draw = ImageDraw.Draw(img)
    draw.polygon(xy_list, fill="white")

    # create the logical mask for patch selection in the return variable
    return np.array(img) > 0


def get_priority_location_arrays_dict(run_parameters):
    """ priority_loc_array_dict = get_priority_location_arrays_dict(run_parameters)
    """
    #                                                           define the return variable
    priority_loc_array_dict = defaultdict(dict)

    #                                                           assign local names
    wsi_filename = run_parameters['wsi_filename']
    csv_file_name = run_parameters['csv_file_name']
    xml_file_name = run_parameters['xml_file_name']
    patch_select_method = run_parameters['patch_select_method']

    image_level = run_parameters['image_level']

    thumbnail_divisor = run_parameters['thumbnail_divisor']

    patch_height = run_parameters['patch_height']
    patch_width = run_parameters['patch_width']

    threshold = run_parameters['threshold']

    if 'patch_stride_fraction' in run_parameters:
        patch_stride = run_parameters['patch_stride_fraction']
    else:
        patch_stride = 1.0

    #                           Open image file
    os_im_obj = openslide.OpenSlide(wsi_filename)
    #                           Get scale calculation necessities, and thumbnail image
    image_dimensions = os_im_obj.dimensions
    level_downsample = os_im_obj.level_downsamples[image_level]
    thumbnail_size = (image_dimensions[0] // thumbnail_divisor, image_dimensions[1] // thumbnail_divisor)
    thumbnail_image = os_im_obj.get_thumbnail(thumbnail_size)

    #                           Guard openslide.get_thumbnail misbehavior - really - it may be off by one!
    thumbnail_size = thumbnail_image.size

    #                           Close image file
    os_im_obj.close()

    #                           Get initial mask by pre-annotation methods
    mask_im = get_sample_selection_mask(thumbnail_image, patch_select_method, run_parameters=None)

    #                           Read the xml and csv files into priorities: coordinates & co dict
    priority_dict = get_ordered_priority_label_coords_dict(xml_file_name, csv_file_name)
    for p, p_dict in priority_dict.items():

        p_dict['level_downsample'] = level_downsample
        label = p_dict['label']

        this_mask = get_region_mask(p_dict['vertices'], thumbnail_divisor, thumbnail_size)
        mask_im = np.logical_and(this_mask, mask_im)

        if mask_im.sum() > 0:
            patch_location_array = []

            #                   patches search - limit to positive mask area
            thumb_row_start, thumb_row_stop = get_select_bounds_from_mask(mask_im, 'y')
            row_start, row_stop = thumb_row_start * thumbnail_divisor, thumb_row_stop * thumbnail_divisor

            thumb_col_start, thumb_col_stop = get_select_bounds_from_mask(mask_im, 'x')
            col_start, col_stop = thumb_col_start * thumbnail_divisor, thumb_col_stop * thumbnail_divisor

            #                   get the rows for image level & rescale to full size wsi
            # scale_patch_height = patch_height
            rows_fence_array = get_strided_fence_array(patch_height, patch_stride,
                                                       row_start // level_downsample,
                                                       row_stop // level_downsample)
            rows_fence_array = (rows_fence_array * level_downsample).astype(np.int)

            #                   get the columns for image level & rescale to full size wsi
            # scale_patch_width = patch_width
            cols_fence_array = get_strided_fence_array(patch_width, patch_stride,
                                                       col_start / level_downsample,
                                                       col_stop / level_downsample)
            cols_fence_array = (cols_fence_array * level_downsample).astype(np.int)

            #       zip scaled Fence Arrays for rows & cols iterators
            #                   iterator for rows:  (top_row, bottom_row, full_scale_row_number)
            it_rows = zip(rows_fence_array[:, 0] // thumbnail_divisor,
                          rows_fence_array[:, 1] // thumbnail_divisor,
                          rows_fence_array[:, 0])

            #                   variables to construct in-loop cols iterator:
            lft_cols = cols_fence_array[:, 0] // thumbnail_divisor
            rgt_cols = cols_fence_array[:, 1] // thumbnail_divisor
            cols_array = cols_fence_array[:, 0]

            for tmb_row_top, tmb_row_bot, row_n in it_rows:

                #               iterator for cols:  (left_column, right_column, full_scale_column_number)
                it_cols = zip(lft_cols, rgt_cols, cols_array)

                for tmb_col_lft, tmb_col_rgt, col_n in it_cols:

                    #           select patch if selected patch pixels sum to more than threshold (default=0)
                    if (mask_im[tmb_row_top:tmb_row_bot, tmb_col_lft:tmb_col_rgt]).sum() > threshold:
                        #       add the image level scale row and column of the upper left corner to the list
                        patch_location_array.append((col_n, row_n))

            #                   add to return dict only if patches were found
            if len(patch_location_array) > 0:
                p_dict['patch_location_array'] = patch_location_array
                priority_loc_array_dict[p] = p_dict

    return priority_loc_array_dict


class AnnotationPatchesGenerator():
    def __init__(self, run_parameters):

        self.image_level = int(run_parameters['image_level'])
        self.patch_size = (int(run_parameters['patch_width']), int(run_parameters['patch_height']))
        self.os_obj = openslide.OpenSlide(run_parameters['wsi_filename'])

        self.plad_dict = get_priority_location_arrays_dict(run_parameters)
        self.plad_key_list = list(self.plad_dict.keys())
        self.plad_key = 0
        if len(self.plad_dict) < 1:
            self.stop_iteration = True
            self.p_dict = {}
            self.label = None
            self.loc_arr = [[]]
            self.p_idx = -1

        else:
            self.stop_iteration = False
            self.p_dict = self.plad_dict[self.plad_key_list[self.plad_key]]
            self.label = self.p_dict['label']
            self.loc_arr = self.p_dict['patch_location_array']
            self.p_idx = -1

    def __del__(self):
        self.os_obj.close()

    def next_patch(self):

        self.p_idx += 1

        if self.p_idx < len(self.loc_arr) and self.stop_iteration == False:
            patch_dict = {'label': self.label, 'patch_location': self.loc_arr[self.p_idx]}
            location = (self.loc_arr[self.p_idx][0], self.loc_arr[self.p_idx][1])
            patch_dict['patch_image'] = self.os_obj.read_region(location, self.image_level, self.patch_size)

            return patch_dict

        elif self.plad_key + 1 < len(self.plad_key_list) and self.stop_iteration == False:
            self.plad_key = self.plad_key + 1
            self.p_dict = self.plad_dict[self.plad_key_list[self.plad_key]]
            self.label = self.p_dict['label']
            self.loc_arr = self.p_dict['patch_location_array']

            self.p_idx = 0
            patch_dict = {'label': self.label, 'patch_location': self.loc_arr[self.p_idx]}

            location = (self.loc_arr[self.p_idx][0], self.loc_arr[self.p_idx][1])
            patch_dict['patch_image'] = self.os_obj.read_region(location, self.image_level, self.patch_size)

            return patch_dict

        else:
            raise StopIteration()


def verify_files_list(files_list):
    """ files_not_found = verify_files_list(files_list)
    """
    files_not_found_list = []
    for file_name in files_list:
        if os.path.isfile(file_name) == False:
            files_not_found_list.append(file_name)

    return files_not_found_list


def get_run_location_parameters_or_defaults(run_parameters):
    """ Usage: location_parameters = get_run_location_parameters_or_defaults(run_parameters)
    input data cleanup task
    Args:
        run_parameters:         required keys
                                    wsi_filename
                                    output_dir
                                optional keys
                                    class_label
                                    file_ext
    Returns:
        location_parameters:    with keys
                                    output_dir          created if non-existannt
                                    file_name_base      wsi_filename wo path & extension (w posix cleanup)
                                    class_label         default is empty str             (w posix cleanup)
                                    file_ext            default is .jpg
    """
    location_parameters = {}

    image_file_name = run_parameters['wsi_filename']
    output_dir = run_parameters['output_dir']

    if 'class_label' in run_parameters:
        class_label = run_parameters['class_label']
    else:
        class_label = ''

    if 'file_ext' in run_parameters:
        file_ext = run_parameters['file_ext']
        if file_ext[0] != '.':
            file_ext = '.' + file_ext
    else:
        file_ext = '.jpg'

    # check / ceate the output directory
    if os.path.isdir(output_dir) == False:
        print('creating output directory:\n%s\n' % (output_dir))
        os.makedirs(output_dir)

    # prepare name generation dictionary
    _, file_name_base = os.path.split(image_file_name)
    file_name_base, _ = os.path.splitext(file_name_base)

    # sanitize case_id, class_label & file_ext so that they may be decoded - warns user if parameter changes
    file_name_base, class_label = patch_name_parts_clean_with_warning(file_name_base, class_label)

    # assign output parameters
    location_parameters['output_dir'] = output_dir
    location_parameters['file_ext'] = file_ext
    location_parameters['class_label'] = class_label  # may be empty string
    location_parameters['file_name_base'] = file_name_base

    return location_parameters


def run_annotated_patches(run_parameters):
    """ Usage: _ = run_annotated_patches(run_parameters)
    """
    method = run_parameters['method']
    wsi_filename = run_parameters['wsi_filename']
    xml_file_name = run_parameters['xml_file_name']
    csv_file_name = run_parameters['csv_file_name']

    files_not_found = verify_files_list([wsi_filename, xml_file_name, csv_file_name])

    if len(files_not_found) > 0:
        for file_name in files_not_found:
            print('Failed to find file:', file_name)
        return None

    location_parameters = get_run_location_parameters_or_defaults(run_parameters)
    output_dir = location_parameters['output_dir']
    file_ext = location_parameters['file_ext']
    class_label = location_parameters['class_label']
    file_name_base = location_parameters['file_name_base']

    patch_image_name_dict = {'case_id': file_name_base, 'file_ext': file_ext}

    patch_generator_obj = AnnotationPatchesGenerator(run_parameters)

    if method == 'annotations_to_dir':
        patch_number = -1
        while True:
            try:
                patch_dict = patch_generator_obj.next_patch()
                if len(class_label) > 0:
                    patch_image_name_dict['class_label'] = class_label + '_' + patch_dict['label']
                else:
                    patch_image_name_dict['class_label'] = patch_dict['label']
                patch_image_name_dict['location_x'] = patch_dict['patch_location'][0]
                patch_image_name_dict['location_y'] = patch_dict['patch_location'][1]
                patch_name = dict_to_patch_name(patch_image_name_dict)
                patch_full_name = os.path.join(output_dir, patch_name)
                # write the file
                patch_dict['patch_image'].convert('RGB').save(patch_full_name)
                patch_number += 1

            except StopIteration:
                print('%i images written' % (patch_number + 1))
                break


    elif method == 'annotations_to_tfrecord':
        tfrecord_file_name = file_name_base + '.tfrecords'
        tfrecord_file_name = os.path.join(output_dir, tfrecord_file_name)

        with tf_io.TFRecordWriter(tfrecord_file_name) as writer:
            seq_number = 0
            while True:
                try:
                    patch_dict = patch_generator_obj.next_patch()
                    if len(class_label) > 0:
                        patch_image_name_dict['class_label'] = class_label + '_' + patch_dict['label']
                    else:
                        patch_image_name_dict['class_label'] = patch_dict['label']

                    patch_image_name_dict['location_x'] = patch_dict['patch_location'][0]
                    patch_image_name_dict['location_y'] = patch_dict['patch_location'][1]
                    patch_name = dict_to_patch_name(patch_image_name_dict)

                    image_string = patch_dict['patch_image'].convert('RGB')

                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')

                    try:
                        image_string.save(tmp.name)
                        image_string = open(tmp.name, 'rb').read()

                    except:
                        print('Image write-read exception with patch # %i, named:\n%s' % (seq_number, patch_name))
                        pass

                    finally:
                        os.unlink(tmp.name)
                        tmp.close()

                    tf_example_obj = tf_imp_dict(image_string,
                                                 label=seq_number,
                                                 image_name=bytes(patch_name, 'utf8'),
                                                 class_label=bytes(class_label, 'utf8'))

                    writer.write(tf_example_obj.SerializeToString())
                    seq_number += 1

                except StopIteration:
                    print('%5i images written to %s' % (seq_number, tfrecord_file_name))
                    break


"""                             Use Case 3 

        Givin a WSI and another WSI, do image registration, export pair of patches into TFRecords.
        
        One Whole Slide Image will be 'fixed' and the other WSI will be the 'float' image.
"""


def run_registration_pairs(run_parameters):
    """ Usage:  registration_pair_to_directory(run_parameters)

    Args:       run_parameters
                    method              one of - [registration_to_dir, registration_to_tfrecord]
                    wsi_filename        'fixed' image
                    wsi_floatname       'float' image
                    offset_data_file    csv with (truth_offset_x, truth_offset_y)
                    patch_width         pixels width of patch selection
                    patch_height        pixels height of patch selection
                    image_level         openslide pyramid image level 0, 1, ...
                    class_label         label for train-test
                    output_dir          where the patches or tfrecord will be wtitten
                (optional run_parameters)
                    file_ext            .jpg is default, and only one implemented for tensorflow in this version
                                        (note that .png is much better compression but much, much slower)

    Returns:
        (nothing)   writes image files or tfrecord depending on run_parameters['method'] input

    """
    method = run_parameters['method']
    # insert the offset into the run_parmaters:
    if os.path.isfile(run_parameters['offset_data_file']):
        offset_df = pd.read_csv(run_parameters['offset_data_file'])

        offset_x = int(round(offset_df['truth_offset_x'].iloc[0]))
        offset_y = int(round(offset_df['truth_offset_y'].iloc[0]))

        run_parameters['offset_x'] = offset_x
        run_parameters['offset_y'] = offset_y

        float_offset_x = -1 * offset_x
        float_offset_y = -1 * offset_y

    elif 'offset_x' in run_parameters and 'offset_y' in run_parameters:
        float_offset_x = -1 * run_parameters['offset_x']
        float_offset_y = -1 * run_parameters['offset_y']

    # form named parameters
    patch_size = (run_parameters['patch_width'], run_parameters['patch_height'])

    image_level = run_parameters['image_level']

    image_file_name = run_parameters['wsi_filename']

    if os.path.isfile(image_file_name) == False:
        print('\n\n\tFile not found:\n\t%s\n\n' % (image_file_name))
        return

    output_dir = run_parameters['output_dir']
    class_label = run_parameters['class_label']

    if 'file_ext' in run_parameters:
        file_ext = run_parameters['file_ext']
        if file_ext[0] != '.':
            file_ext = '.' + file_ext
    else:
        file_ext = '.jpg'

    # check / ceate the output directory
    if os.path.isdir(output_dir) == False:
        print('creating output directory:\n%s\n' % (output_dir))
        os.makedirs(output_dir)

    # prepare name generation dictionary
    _, file_name_base = os.path.split(image_file_name)
    file_name_base, _ = os.path.splitext(file_name_base)

    # sanitize case_id, class_label & file_ext so that they may be decoded - warns user if parameter changes
    file_name_base, class_label = patch_name_parts_clean_with_warning(file_name_base, class_label)

    patch_image_name_dict = {'case_id': file_name_base, 'class_label': class_label, 'file_ext': file_ext}

    # get the patch image generator
    fixed_im_generator = PatchImageGenerator(run_parameters)

    # Open the float image
    wsi_float_obj = openslide.OpenSlide(run_parameters['wsi_floatname'])
    X, Y = wsi_float_obj.dimensions
    X_dim = (0, X)
    Y_dim = (0, Y)

    if method == 'registration_to_dir':
        stop_teration = False
        patch_dict = fixed_im_generator.next_patch()
        patch_number = -2
        while stop_teration == False:
            # form the patch filename
            patch_image_name_dict['location_x'] = patch_dict['image_level_x']
            patch_image_name_dict['location_y'] = patch_dict['image_level_y']
            patch_name = dict_to_patch_name(patch_image_name_dict)
            patch_full_name = os.path.join(output_dir, patch_name)

            # get the full-scale image location of the patch
            x1 = patch_dict['level_0_x'] + float_offset_x
            y1 = patch_dict['level_0_y'] + float_offset_y

            # define the patch full boundry
            x_b = [x1, x1 + patch_size[0]]
            y_b = [y1, y1 + patch_size[1]]

            # check bounds, get float image, write the pair
            if check_patch_in_bounds(x_b, y_b, X_dim, Y_dim) == True:
                flot_im = wsi_float_obj.read_region((x1, y1), image_level, patch_size)
                im_pair = im_pair_hori(patch_dict['patch_image'], flot_im)

                # write the file
                im_pair.convert('RGB').save(patch_full_name)

            try:
                patch_dict = fixed_im_generator.next_patch()
                patch_number = patch_dict['patch_number']
            except:
                print('%i images written' % (patch_number - 2))
                stop_teration = True
                pass

    elif method == 'registration_to_tfrecord':
        tfrecord_file_name = file_name_base + '.tfrecords'
        tfrecord_file_name = os.path.join(output_dir, tfrecord_file_name)

        with tf_io.TFRecordWriter(tfrecord_file_name) as writer:
            seq_number = 0
            while True:
                try:
                    patch_dict = fixed_im_generator.next_patch()
                    patch_image_name_dict['location_x'] = patch_dict['image_level_x']
                    patch_image_name_dict['location_y'] = patch_dict['image_level_y']
                    patch_name = dict_to_patch_name(patch_image_name_dict)

                    # get the full-scale image location of the patch
                    x1 = patch_dict['level_0_x'] + float_offset_x
                    y1 = patch_dict['level_0_y'] + float_offset_y

                    # define the patch full boundry
                    x_b = [x1, x1 + patch_size[0]]
                    y_b = [y1, y1 + patch_size[1]]

                    # check bounds, get float image, write the pair
                    if check_patch_in_bounds(x_b, y_b, X_dim, Y_dim) == True:
                        flot_im = wsi_float_obj.read_region((x1, y1), image_level, patch_size)
                        im_pair = im_pair_hori(patch_dict['patch_image'], flot_im)
                        image_string = im_pair.convert('RGB')

                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                        try:
                            image_string.save(tmp.name)
                            image_string = open(tmp.name, 'rb').read()

                        except:
                            print('Image write-read exception at patch: %i, named:\n%s'%(seq_number, patch_name))
                            pass

                        finally:
                            os.unlink(tmp.name)
                            tmp.close()

                        tf_example_obj = tf_imp_dict(image_string,
                                                     label=seq_number,
                                                     image_name=bytes(patch_name, 'utf8'),
                                                     class_label=bytes(class_label, 'utf8'))

                        writer.write(tf_example_obj.SerializeToString())
                        seq_number += 1

                except StopIteration:
                    print('%5i images written to %s' % (seq_number, tfrecord_file_name))
                    break

        if os.path.isfile(tfrecord_file_name):
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(tfrecord_file_name)
            if size > 0:
                print('TFRecord file size:%i\n%s\n'%(size, tfrecord_file_name))


    # Close the float image
    try:
        del fixed_im_generator
        wsi_float_obj.close()
    except:
        pass



"""                             Use Case 4 

        Givin a WSI & TFRecord, generate a masked Thumbnail 
        
        (graphic representation of the WSI in the TFRecord)
"""

def image_file_to_patches_directory_for_image_level(run_parameters):
    """ Usage: image_file_to_patches_directory_for_image_level(run_parameters)

    Args:
        run_parameters:         (python dict with these keys)
                                wsi_filename:           file name (with valid path)
                                output_dir:             writeable directory for the tfrecord
                                class_label:            label for all images
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                file_ext:               default is '.jpg' ('.png') was also tested
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
                                threshold:              minimimum sum of thresholded image (default = 0)

    Returns:                    None - writes images to output_dir (possibly many)
                                (prints number of images written)
    """
    # explicitly name the input parameters
    image_file_name = run_parameters['wsi_filename']
    if os.path.isfile(image_file_name) == False:
        print('\n\n\tFile not found:\n\t%s\n\n'%(image_file_name))
        return
    output_dir = run_parameters['output_dir']
    class_label = run_parameters['class_label']

    if 'file_ext' in run_parameters:
        file_ext = run_parameters['file_ext']
        if file_ext[0] != '.':
            file_ext = '.' + file_ext
    else:
        file_ext = '.jpg'

    # check / ceate the output directory
    if os.path.isdir(output_dir) == False:
        print('creating output directory:\n%s\n' % (output_dir))
        os.makedirs(output_dir)

    # prepare name generation dictionary
    _, file_name_base = os.path.split(image_file_name)
    file_name_base, _ = os.path.splitext(file_name_base)

    # sanitize case_id, class_label and file_ext so that they may be decoded - warn user input parameter changed
    file_name_base, class_label = patch_name_parts_clean_with_warning(file_name_base, class_label)

    patch_image_name_dict = {'case_id': file_name_base, 'class_label': class_label, 'file_ext': file_ext}

    # get the patch-image generator object
    patch_generator_obj = PatchImageGenerator(run_parameters)
    patch_number = -2
    while True:
        # iterate the patch_generator_obj untill empty
        try:
            patch_dict = patch_generator_obj.next_patch()
            patch_image_name_dict['location_x'] = patch_dict['image_level_x']
            patch_image_name_dict['location_y'] = patch_dict['image_level_y']
            patch_name = dict_to_patch_name(patch_image_name_dict)
            patch_full_name = os.path.join(output_dir, patch_name)
            # write the file
            patch_dict['patch_image'].convert('RGB').save(patch_full_name)
            patch_number = patch_dict['patch_number']

        except StopIteration:
            print('%i images written' % (patch_number + 1))
            break


"""
                            visualization | examination
"""
def write_tfrecord_marked_thumbnail_image(run_parameters):
    """ Usage: write_tfrecord_marked_thumbnail_image(run_parameters)
    Args:
        run_parameters:         (python dict with these keys)
                                tfrecord_file_name:     tfrecord filename created from the wsi_filename
                                wsi_filename:           file name (with valid path)
                                output_dir:             writeable directory for the tfrecord
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                border_color:           red, blue, green

                                (Optional)
                                image_level:            defaults to 0
                                output_file_name:       defaults to output_dir + wsi_filename (base) + .jpg

    Returns:                    None - writes images to output_dir (possibly many)
                                (prints number of images written)
    """
    output_dir = run_parameters['output_dir']
    if 'output_file_name' in run_parameters:
        output_file_name = os.path.join(output_dir, run_parameters['output_file_name'])
    else:
        wsi_filename = run_parameters['wsi_filename']
        _, wsi_file_base = os.path.split(wsi_filename)
        wsi_file_base, _ = os.path.splitext(wsi_file_base)
        output_file_name = os.path.join(output_dir, wsi_file_base + '_thumb_preview.jpg')
    thumb_preview = tf_record_to_marked_thumbnail_image(run_parameters)
    thumb_preview.save(output_file_name)
    print('tfrecord thumnail preview saved to:', output_file_name)


def tf_record_to_marked_thumbnail_image(run_parameters):
    """ Usage: thumb_preview = tf_record_to_marked_thumbnail_image(run_parameters)

    Args:
        run_parameters:         (python dict with these keys)
                                tfrecord_file_name:     tfrecord filename created from the wsi_filename
                                wsi_filename:           file name (with valid path)
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image

                                (Optional)
                                image_level:            defaults to 0
                                border_color:           red, blue, green

    Returns:
        thumb_preview:          PIL image with patch locations marked

    """
    #                   unpack - name the variables
    tfrecord_file_name = run_parameters['tfrecord_file_name']
    wsi_filename = run_parameters['wsi_filename']
    thumbnail_divisor = run_parameters['thumbnail_divisor']
    if 'border_color' in run_parameters:
        border_color = run_parameters['border_color']
    else:
        border_color = 'blue'

    if 'image_level' in run_parameters:
        image_level = run_parameters['image_level']
    else:
        image_level = 0

    #                     OpenSlide open                      #
    os_im_obj = openslide.OpenSlide(wsi_filename)

    #                   get the size of the image at this image level
    obj_level_diminsions = os_im_obj.level_dimensions
    pixels_width = obj_level_diminsions[image_level][0]
    pixels_height = obj_level_diminsions[image_level][1]

    #                   get the thumbnail image scaled to the thumbnail divisor
    thumbnail_size = (pixels_width // thumbnail_divisor, pixels_height // thumbnail_divisor)
    thumb_preview = os_im_obj.get_thumbnail(thumbnail_size)
    os_im_obj.close()
    #                     OpenSlide close                      #

    #                   rectangle-drawing object for the thumbnail preview image
    thumb_draw = ImageDraw.Draw(thumb_preview)

    iterable_tfrecord = get_iterable_tfrecord(tfrecord_file_name)
    scaled_patch_width = None
    scaled_patch_height = None
    for dict_one in iterable_tfrecord:
        scaled_patch_height = dict_one['height'] // thumbnail_divisor - 1
        scaled_patch_width = dict_one['width'] // thumbnail_divisor - 1
        break

    iterable_tfrecord = get_iterable_tfrecord(tfrecord_file_name)
    for patch_dict in iterable_tfrecord:
        im_name = patch_dict['image_name'].numpy().decode('utf-8')
        patch_name_dict = patch_name_to_dict(im_name)
        c = patch_name_dict['location_x']
        r = patch_name_dict['location_y']

        # define the patch location by upper left corner = (column, row)
        ulc = (c // thumbnail_divisor, r // thumbnail_divisor)

        #               lower right corner = upper left corner + scaled patch sizes
        lrc = (ulc[0] + scaled_patch_width, ulc[1] + scaled_patch_height)

        #               draw the rectangle from the upper left corner to the lower right corner
        thumb_draw.rectangle((ulc, lrc), outline=border_color, fill=None)

    return thumb_preview


def get_patch_locations_preview_image_for_image_level(run_parameters):
    """ Usage:
    mask_image, thumb_preview, patch_location_array = get_patch_locations_preview_image_for_image_level(run_parameters)

    create viewable images to show patch locations

    Args (run_parameters):  python dict.keys()
                                wsi_filename:           file name (with valid path)
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
                                threshold:              sum of thresholded image minimimum (default = 0)
                                image_level:            openslide image pyramid level 0,1,2,...

                            Optional keys()
                                border_color:           patch-box representation color red, blue, green, ...
    Returns:
        mask_image:             black & white image of the mask
        thumb_preview:          thumbnail image with patch locations marked
        patch_location_array:   list of patch locations used [(row, col), (row, col),... ]

    """
    #                   unpack - name the variables
    wsi_filename = run_parameters['wsi_filename']
    patch_select_method = run_parameters['patch_select_method']
    thumbnail_divisor = run_parameters['thumbnail_divisor']

    if 'border_color' in run_parameters:
        border_color = run_parameters['border_color']
    else:
        border_color = 'blue'

    #                   scale the patch size to the thumbnail image
    scaled_patch_height = run_parameters['patch_height'] // thumbnail_divisor - 1
    scaled_patch_width = run_parameters['patch_width'] // thumbnail_divisor - 1

    if 'image_level' in run_parameters:
        image_level = run_parameters['image_level']
    else:
        image_level = 0

    #                     OpenSlide open                      #
    os_im_obj = openslide.OpenSlide(wsi_filename)

    #                   get the size of the image at this image level
    obj_level_diminsions = os_im_obj.level_dimensions
    pixels_width = obj_level_diminsions[image_level][0]
    pixels_height = obj_level_diminsions[image_level][1]

    #                   get the thumbnail image scaled to the thumbnail divisor
    thumbnail_size = (pixels_width // thumbnail_divisor, pixels_height // thumbnail_divisor)
    thumb_preview = os_im_obj.get_thumbnail(thumbnail_size)
    os_im_obj.close()
    #                     OpenSlide close                      #

    #                   get the mask image for this patch_select_method
    mask_image = get_sample_selection_mask(thumb_preview, patch_select_method)
    #                   convert it from a binary matrix to a viewable image
    mask_image = tip.Image.fromarray(np.uint8(mask_image * 255), 'L')

    #                   rectangle-drawing object for the thumbnail preview image
    thumb_draw = ImageDraw.Draw(thumb_preview)

    #                   thumbnail-scaled patch locations to draw rectangles
    patch_location_array = get_patch_location_array_for_image_level(run_parameters)

    #                   draw the rectangles on the thumb_preview image
    for c, r in patch_location_array[:]:
        #               upper left corner = scaled column & row location of patch on thumbnail image
        ulc = (c // thumbnail_divisor, r // thumbnail_divisor)
        #               lower right corner = upper left corner + scaled patch size
        lrc = (ulc[0] + scaled_patch_width, ulc[1] + scaled_patch_height)

        #               draw the rectangle from the upper left corner to the lower right corner
        thumb_draw.rectangle((ulc, lrc), outline=border_color, fill=None)

    return mask_image, thumb_preview, patch_location_array


def write_mask_preview_set(run_parameters):
    """
    Args (run_parameters):  python dict.keys()
                                wsi_filename:           file name (with valid path)
                                output_dir:             where the three files will be written
                                border_color:           patch-box representation color 'red', 'blue' etc
                                patch_height:           patch size = (patch_width, patch_height)
                                patch_width:            patch size = (patch_width, patch_height)
                                thumbnail_divisor:      wsi_image full size divisor to create thumbnail image
                                patch_select_method:    'threshold_rgb2lab' or 'threshold_otsu'
    Returns:
        None:               Writes three files:
                                wsi_basename_marked_thumb
                                wsi_basename_mask
                                wsi_basename_patch_locations
    """
    output_dir = run_parameters['output_dir']
    wsi_filename = run_parameters['wsi_filename']
    _, wsi_file_base = os.path.split(wsi_filename)
    wsi_file_base, _ = os.path.splitext(wsi_file_base)

    #               get the two images and the location array
    mask_image, thumb_preview, patch_location_array = get_patch_locations_preview_image_for_image_level(run_parameters)

    #               name and write the thumb_preview image
    thumb_preview_filename = os.path.join(output_dir, wsi_file_base + 'marked_thumb.jpg')
    with open(thumb_preview_filename, 'w') as fh:
        thumb_preview.save(fh)

    #               name and write the mask_preview image
    mask_preview_filename = os.path.join(output_dir, wsi_file_base + 'mask.jpg')
    with open(mask_preview_filename, 'w') as fh:
        mask_image.save(fh)

    #               name, build and write a dataframe for the upper left corners list
    location_array_filename = os.path.join(output_dir, wsi_file_base + 'patch_locations.tsv')
    patchlocation_df = pd.DataFrame(patch_location_array, columns=['row', 'col'])
    patchlocation_df.index.name = '#'
    patchlocation_df.to_csv(location_array_filename, sep='\t')

    #               print the output files location
    print('mask preview set saved:\n\t%s\n\t%s\n\t%s' % (thumb_preview_filename,
                                                         mask_preview_filename,
                                                         location_array_filename))
