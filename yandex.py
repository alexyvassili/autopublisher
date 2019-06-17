import urllib.parse
import urllib.request
import json
import subprocess


def load_image_from_yandex_mail_link(link):
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key="

    encoded_link = urllib.parse.quote(link)
    response = urllib.request.urlopen(api_url + encoded_link).read()
    response_json = json.loads(response)
    download_href = response_json["href"]
    parsed_href = urllib.parse.urlparse(download_href)
    params = {param.split('=')[0]: param.split('=')[1] for param in parsed_href.query.split('&')}
    filename = params['filename']
    subprocess.call(['wget', f'{download_href}', '-O', filename])
