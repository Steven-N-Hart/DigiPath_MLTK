"""
main function for ./digipath.toolkit.py

Usage:
python3 digipath_mltk.run_toolkit -run_directory ./ -run_file run_parameters_file.yml

"""

def image_2_tfrecord(run_parameters):
    from digipath_mltk.toolkit import wsi_file_to_patches_tfrecord
    wsi_file_to_patches_tfrecord(run_parameters)

def tfrecord_2_masked_thumb(run_parameters):
    from digipath_mltk.toolkit import write_tfrecord_marked_thumbnail_image
    write_tfrecord_marked_thumbnail_image(run_parameters)

def wsi_2_patches_dir(run_parameters):
    from digipath_mltk.toolkit import image_file_to_patches_directory_for_image_level
    image_file_to_patches_directory_for_image_level(run_parameters)

def write_mask_preview(run_parameters):
    from digipath_mltk.toolkit import write_mask_preview_set
    write_mask_preview_set(run_parameters)

def registration_functions(run_parameters):
    from digipath_mltk.toolkit import run_registration_pairs
    run_registration_pairs(run_parameters)

def annotation_functions(run_parameters):
    from digipath_mltk.toolkit import run_annotated_patches
    run_annotated_patches(run_parameters)

SELECT = {"wsi_to_tfrecord": image_2_tfrecord,
          "tfrecord_to_masked_thumb": tfrecord_2_masked_thumb,
          'wsi_to_patches_dir': wsi_2_patches_dir,
          'wrte_mask_preview_set': write_mask_preview,
          'registration_to_dir': registration_functions,
          'registration_to_tfrecord': registration_functions,
          'annotations_to_dir': annotation_functions,
          'annotations_to_tfrecord': annotation_functions}

def main():
    import sys
    from digipath_mltk.toolkit import get_run_directory_and_run_file, get_run_parameters
    run_directory, run_file = get_run_directory_and_run_file(sys.argv[1:])
    run_parameters = get_run_parameters(run_directory, run_file)

    SELECT[run_parameters['method']](run_parameters)

if __name__ == "__main__":
    main()
