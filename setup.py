"""
# 						Development install notes

# Simple: development install from local src referencing directory with setup.py
pip3 install --upgrade ../DigiPath_MLTK

# Create dist files:
#				install packages needed to build distribution files
pip3 install --upgrade setuptools wheel

#				build package in the dist/ directory
python3 setup.py sdist bdist_wheel

#				install package needed to upload the distribution
python3 -m pip install --user --upgrade twine

# Upload distribution files to PYPI TEST SITE (allows viewing of pypi install / doc page for development):
#				username and password required: use __token__ and the API token created in your account
python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/digipath_mltk-x.x.x*

#				after successful upload to PYPI TEST SITE: install the package with pip
pip3 install -i https://test.pypi.org/simple/ digipath_mltk==x.x.x
"""
from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as fh:
    readme_text = fh.read()

setup(name='digipath_mltk',
	version='0.0.0',
	long_description=readme_text,
	long_description_content_type='text/markdown',
	author='DigiPath_MLTK development team',
	url='https://ncsa.github.io/DigiPath_MLTK/',
	classifiers=['License :: OSI Approved :: MIT License', 
	'Programming Language :: Python :: 3.5', 
	'Programming Language :: Python :: 3.6',
	'Programming Language :: Python :: 3.7',
	'Programming Language :: Python :: 3.8',
	"Operating System :: OS Independent"],
	python_requires='>=3.5',
	packages=['digipath_mltk'],
	project_urls={'Source': 'https://github.com/ncsa/DigiPath_MLTK'})

