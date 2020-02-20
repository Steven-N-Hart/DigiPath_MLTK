# Parameterized large image pre-processing with _*pychunklbl.toolkit*_
The package module _*pychunklbl.toolkit*_ provides eight parameterized functions designed to work with large image files and provide pre-processing for machine learning.

The package module is intended developers to create machine learning datasets leveraging the [openslide](https://openslide.org/) library for usage with [tensorflow 2.0](https://www.tensorflow.org/).

****
## Installation
```
pip install digipath_mltk

# requires python 3.5 or later
pip3 install -r requirements.txt
```
### Development install from clone in /DigiPath_MLTK/ directory:
```
pip3 install -r requirements.txt
pip3 install --upgrade ../DigiPath_MLTK
```

****
### Command line examples

Images used in the examples below was downloaded from [openslide data](http://openslide.cs.cmu.edu/download/openslide-testdata/), the other data files are in the repository data/ directory. <br>

#### Find the patches in a wsi file and write to an image file for preview.
```
python3 -m digipath_mltk.cli -m write_mask_preview_set -i yourpath/images/CMU-1-Small-Region.svs -o results
```

#### Find the patches in a wsi file and write to a directory.
```
python3 -m digipath_mltk.cli -m wsi_to_patches_dir -i CMU-1-Small-Region.svs -o results
```

#### Find the patches in a wsi file and write to a .tfrecords file.
```
python3 -m digipath_mltk.cli -m wsi_to_tfrecord -i CMU-1-Small-Region.svs -o results
```

#### View the patch locations in a .tfrecoreds file.
```
python3 -m digipath_mltk.cli -m tfrecord_to_masked_thumb -i CMU-1-Small-Region.svs -r CMU-1-Small-Region.tfrecords -o results
```

` ( test data not currently available in DigiPath_MLTK repository for the following examples ) `

#### Find pairs of patches with registration offset in two wsi files and write to a directory.
```
python3 -m digipath_mltk.cli -m registration_to_dir -i wsi_fixed.tiff -f wsi_float.tiff -D wsi_pair_sample_offset.csv -o results
```

#### Find pairs of patches with registration offset in two wsi files and write to a tfrecords file.
```
python3 -m digipath_mltk.cli -m registration_to_tfrecord -i  wsi_fixed.tiff -f wsi_float.tiff -D wsi_pair_sample_offset.csv -o results
```

#### Find the patches in a wsi file defined in an annotations file with a priority file and write to a directory.
```
python3 -m digipath_mltk.cli -m annotations_to_dir -i wsi_float.tiff -p wsi_float_annotation.csv -a wsi_float_annotation.xml -o results
```

#### Find the patches in a wsi file defined in an annotations file with a priority file and write to a tfrecords file.
```
python3 -m digipath_mltk.cli -m annotations_to_tfrecord -i wsi_float.tiff -p wsi_float_annotation.csv -a wsi_float_annotation.xml -o results
```
