import os
import shutil
from datetime import datetime

import prepare
import publish
import yandex


def current_directory():
    folder = os.getcwd()
    print('Prepare...')
    title, html, jpegs = prepare.news(folder)
    print('Publish...')
    publish.news(title, html, jpegs)


def yandex_disk_link(link):
    from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
    mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + datetime.today().strftime('%Y.%m.%d-%H.%M.%S'))
    os.makedirs(mail_folder)
    try:
        yandex.load_files_from_yandex_disk_folder(link, mail_folder)
        print('Prepare...')
        title, html, jpegs = prepare.news(mail_folder)
        print('Publish...')
        publish.news(title, html, jpegs)
        print('Clear...')
        shutil.rmtree(mail_folder)
    except Exception as e:
        shutil.rmtree(mail_folder)
        raise e


if __name__ == "__main__":
    link = "https://yadi.sk/d/tPEfUcY4nJrtcg"
    yandex_disk_link(link)
