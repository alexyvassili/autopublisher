import os
import subprocess
from datetime import datetime

from document_utils import format_rasp_docx, cd

SOFFICE_PATH = "/opt/libreoffice6.2/program/soffice"


class PrepareException(Exception):
    pass


def check_rasp_folder(folder):
    docxs = [item for item in os.listdir(folder) if  item.endswith('docx')]
    if not docxs:
        raise PrepareException("Can't find word file in mail")
    elif len(docxs) > 1:
        raise PrepareException('Too many word files in mail')

    jpegs = [item for item in os.listdir(folder) if  item.endswith('jpg')]

    if jpegs:
        raise PrepareException('Jpeg in rasp mail found!')


def prepare_rasp(mail_folder):
    RASP_NAME = 'rasp_' + datetime.today().strftime('%Y-%m-%d')
    JPG_NAME = os.path.join(mail_folder, RASP_NAME + '.jpg')

    # rasp folder must contain only one .docx and no jpegs
    check_rasp_folder(mail_folder)

    docxs = [item for item in os.listdir(mail_folder) if  item.endswith('docx')]
    docx_name = docxs[0]
    formatted_docx_name = format_rasp_docx(docx_name, mail_folder)

    if not os.path.exists(formatted_docx_name):
        raise PrepareException(f"Can't find formatted docx: {formatted_docx_name}")

    with cd(mail_folder):
        subprocess.call([SOFFICE_PATH, '--headless', '--convert-to', 'pdf', formatted_docx_name])
        PDF_NAME = formatted_docx_name.split('.')[0] + '.pdf'
        if not os.path.exists(PDF_NAME):
            raise PrepareException(f"Can't find formatted pdf: {formatted_docx_name}")
        subprocess.call(['convert', '-density', '300', PDF_NAME, '-quality', '100', JPG_NAME])
    jpegs = [item for item in os.listdir(mail_folder) if item.endswith('jpg')]
    jpegs.sort()

    if not jpegs:
        raise PrepareException('Can\'t find rasp jpegs')

    return jpegs
