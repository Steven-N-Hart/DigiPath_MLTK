"""
Usage from test/ with internet connection:

python3 download_test_data.py

OpenSlide download page:
https://openslide.org/

file_list = ['CMU-1-Small-Region.svs']

"""
import os.path
import urllib.request

def download_test_data():
    base_url = 'http://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/'
    file_list = ['CMU-1-Small-Region.svs']
    dest_dir = 'data/images'

    for file_name in file_list:
        file_to_download = os.path.join(base_url, file_name)
        destination_file_name = os.path.join(dest_dir, file_name)
        print('download:\n\n\t%s\nto:\n\t%s\n'%(file_to_download, destination_file_name))

        tuple_of_stuff = urllib.request.urlretrieve(file_to_download, destination_file_name)
        print(tuple_of_stuff, '\n')

if __name__ == '__main__':
    download_test_data()

