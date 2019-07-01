import urllib.parse
import urllib.request
import os
import json
import subprocess

from document_utils import unzip_without_structure


def load_from_yandex_disk_link(link, load_folder):
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key="

    encoded_link = urllib.parse.quote(link)
    response = urllib.request.urlopen(api_url + encoded_link).read()
    response_json = json.loads(response)
    download_href = response_json["href"]
    parsed_href = urllib.parse.urlparse(download_href)
    params = {param.split('=')[0]: param.split('=')[1] for param in parsed_href.query.split('&')}
    filename = params['filename']
    subprocess.call(['wget', f'{download_href}', '-O', os.path.join(load_folder, filename)])
    return filename


def load_files_from_yandex_disk_folder(link, target_folder):
    zipped_folder = load_from_yandex_disk_link(link, target_folder)
    unzip_without_structure(os.path.join(target_folder, zipped_folder), target_folder)
    os.remove(os.path.join(target_folder, zipped_folder))
