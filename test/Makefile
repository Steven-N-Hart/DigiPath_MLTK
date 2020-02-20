SCRIPT = integration/call_src_only.py
PKG_SCRIPT = digipath_mltk.cli
PKG_TEST_DATA = ../../DigiPath_MLTK_data/integration_test_data/
RUN_DIR = ../../run_dir/
RUN_FILES = data/run_files
RESULTS_DIR = $(RUN_DIR)/results

PYTHON_NAME = python3

SVS_DATA_FILE = data/images/CMU-1-Small-Region.svs
IM_FMT = .jpg
IM_LVL = 3

MKDIR_P = mkdir -p


# # # # # # #
# Phony targets
# # # # # # #

env_setup:	create_run_dir copy_run_files

unit_test:	unit_test_filename unit_test_fences unit_test_run_parameters unit_test_sample_select

integration_test: test_im_2_tfr test_tfr_2_mthumb test_wsi_2_patches_dir test_write_mask_preview test_registration_pairs_dir test_registration_pairs_tfr test_annotations_to_dir test_annotations_to_tfr

install_short_test: test_pkg_im_2_tfr test_pkg_tfr_2_mthumb test_pkg_wsi_2_patches_dir test_pkg_write_mask_preview
install_long_test: test_pkg_registration_pairs_dir test_pkg_registration_pairs_tfr test_pkg_annotations_to_dir test_pkg_annotations_to_tfr 

installation_test: test_pkg_im_2_tfr test_pkg_tfr_2_mthumb test_pkg_wsi_2_patches_dir test_pkg_write_mask_preview test_pkg_registration_pairs_dir test_pkg_registration_pairs_tfr test_pkg_annotations_to_dir test_pkg_annotations_to_tfr


# # # # # # #
# Test setup
# # # # # # #

create_run_dir:
	$(MKDIR_P) $(RESULTS_DIR)

copy_run_files:
	cp $(RUN_FILES)/*.yml $(RUN_DIR)

download_test_images:
	$(PYTHON_NAME) download_test_data.py

# # # # # # #
# Integration tests
# # # # # # #

test_im_2_tfr:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file wsi_file_to_tfrecord.yml

test_tfr_2_mthumb:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file tfrecord_to_masked_thumb.yml

test_wsi_2_patches_dir:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file wsi_file_to_patches_dir.yml

test_write_mask_preview:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file write_mask_previews.yml

test_registration_pairs_dir:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file registration_pairs_to_dir.yml

test_registration_pairs_tfr:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file registration_pairs_to_tfrecord.yml

test_annotations_to_dir:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file annotations_to_dir.yml

test_annotations_to_tfr:
	$(PYTHON_NAME) $(SCRIPT) -run_directory $(RUN_DIR) -run_file annotations_to_tfrecord.yml


# # # # # # # 
# Uint tests
# # # # # # #

unit_test_filename:
	$(PYTHON_NAME) unittest/test_file_name_encoding.py

unit_test_fences:
	$(PYTHON_NAME) unittest/test_get_fence_array.py
 
unit_test_run_parameters:
	$(PYTHON_NAME) unittest/test_get_run_parameters.py

unit_test_sample_select:
	$(PYTHON_NAME) unittest/test_get_sample_selection_mask.py


# # # # # # #
# Installation tests
# # # # # # #

test_pkg_write_mask_preview:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m write_mask_preview_set -i $(SVS_DATA_FILE) -o $(RESULTS_DIR)

test_pkg_wsi_2_patches_dir:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m wsi_to_patches_dir -i $(SVS_DATA_FILE) -o $(RESULTS_DIR)

test_pkg_im_2_tfr:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m wsi_to_tfrecord -i $(SVS_DATA_FILE) -o $(RESULTS_DIR)

test_pkg_tfr_2_mthumb:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m tfrecord_to_masked_thumb -i $(SVS_DATA_FILE) -r data/tfrecords/CMU-1-Small-Region.tfrecords -o $(RESULTS_DIR)

test_pkg_registration_pairs_dir:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m registration_to_dir -i $(PKG_TEST_DATA)wsi_fixed.tiff -f $(PKG_TEST_DATA)wsi_float.tiff -D $(PKG_TEST_DATA)wsi_pair_sample_offset.csv -l $(IM_FMT) -e $(IM_LVL) -o $(RESULTS_DIR)

test_pkg_registration_pairs_tfr:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m registration_to_tfrecord -i $(PKG_TEST_DATA)wsi_fixed.tiff -f $(PKG_TEST_DATA)wsi_float.tiff -D $(PKG_TEST_DATA)wsi_pair_sample_offset.csv -l $(IM_FMT) -e $(IM_LVL) -o $(RESULTS_DIR)

test_pkg_annotations_to_dir:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m annotations_to_dir -i $(PKG_TEST_DATA)wsi_float.tiff -L $(PKG_TEST_DATA)wsi_float_annotation.csv -a $(PKG_TEST_DATA)wsi_float_annotation.xml -l $(IM_FMT) -e $(IM_LVL) -o $(RESULTS_DIR)

test_pkg_annotations_to_tfr:
	$(PYTHON_NAME) -m $(PKG_SCRIPT) -m annotations_to_tfrecord -i $(PKG_TEST_DATA)wsi_float.tiff -L $(PKG_TEST_DATA)wsi_float_annotation.csv -a $(PKG_TEST_DATA)wsi_float_annotation.xml -l $(IM_FMT) -e $(IM_LVL) -o $(RESULTS_DIR)

