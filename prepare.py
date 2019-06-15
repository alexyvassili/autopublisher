import os
import subprocess
import shutil
from bs4 import BeautifulSoup
from datetime import datetime

from document_utils import format_rasp_docx, cd, resize_jpeg_on_wide_size, docx2html
from file_utils import format_jpeg_name, get_file_size_mb, get_files_for_extension, get_fullpath_files_for_extension

SOFFICE_PATH = "/opt/libreoffice6.2/program/soffice"
IMG_FOR_NEWS_FOLDER = 'img'
WIDE_SIDE_IMAGE = 1024


class PrepareError(Exception):
    pass


def check_rasp_folder(folder):
    docxs = [item for item in os.listdir(folder) if  item.endswith('docx')]
    if not docxs:
        raise PrepareError("Can't find word file in mail")
    elif len(docxs) > 1:
        raise PrepareError('Too many word files in mail')

    jpegs = get_files_for_extension(folder, 'jpg')

    if jpegs:
        raise PrepareError('Jpeg in rasp mail found!')


def rasp(mail_folder):
    RASP_NAME = 'rasp_' + datetime.today().strftime('%Y-%m-%d')
    JPG_NAME = os.path.join(mail_folder, RASP_NAME + '.jpg')

    # rasp folder must contain only one .docx and no jpegs
    check_rasp_folder(mail_folder)

    docxs = get_files_for_extension(mail_folder, 'docx')
    docx_name = docxs[0]
    formatted_docx_name = format_rasp_docx(docx_name, mail_folder)

    if not os.path.exists(formatted_docx_name):
        raise PrepareError(f"Can't find formatted docx: {formatted_docx_name}")

    with cd(mail_folder):
        subprocess.call([SOFFICE_PATH, '--headless', '--convert-to', 'pdf', formatted_docx_name])
        PDF_NAME = formatted_docx_name.split('.')[0] + '.pdf'
        if not os.path.exists(PDF_NAME):
            raise PrepareError(f"Can't find formatted pdf: {formatted_docx_name}")
        subprocess.call(['convert', '-density', '300', PDF_NAME, '-quality', '100', JPG_NAME])
    jpegs = get_files_for_extension(mail_folder, 'jpg')
    jpegs.sort()

    if not jpegs:
        raise PrepareError('Can\'t find rasp jpegs')

    return jpegs


def prepare_jpegs_for_news(jpegs, folder, jpegs_folder):
    """jpegs: full-path jpegs"""
    jpegs_for_news = []
    os.mkdir(jpegs_folder)
    formatted_names_jpegs = {jpeg: format_jpeg_name(jpeg) for jpeg in jpegs}
    for jpeg in jpegs:
        size = get_file_size_mb(jpeg)
        new_jpeg_name = formatted_names_jpegs[jpeg]
        if size > 1.5:
            resize_jpeg_on_wide_size(jpeg, new_jpeg_name, WIDE_SIDE_IMAGE)
        else:
            shutil.copyfile(jpeg, new_jpeg_name)
        jpegs_for_news.append(new_jpeg_name)
    return jpegs_for_news


def prepare_html_for_news(mail_metadata, mail_folder):
    docxs = get_fullpath_files_for_extension(mail_folder, 'docx')
    if not docxs:
        # title, html = get_html_news_from_mail_body(mail_metadata['Body'])
        raise PrepareError("Can\'t search news text in mail body")
    elif len(docxs) > 1:
        raise PrepareError("Found many docx for one news")
    else:
        docx = docxs[0]
        title, html = get_html_news_from_docx(docx)
    return title, html


def get_html_news_from_docx(docx):
    html, messages = docx2html(docx)
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = []
    title = None
    for p in soup.find_all('p'):
        string = str(p)
        if not title:
            title = p.text
            continue
        string = string.replace('<p>',
                                """<p style="text-align: justify; text-indent: 20px;"><span style="font-size: 14pt; line-height: 115%; font-family: 'Times New Roman', 'serif'; color: #000000;">""")
        string = string.replace('</p>', '</span></p>')
        paragraphs.append(string)
    news_html = '\n'.join(paragraphs)
    return title, news_html


def news(mail_metadata, mail_folder):
    jpegs = [os.path.join(mail_folder, item) for item in get_files_for_extension(mail_folder, 'jpg')]
    if not jpegs:
        raise PrepareError('Can\'t publish news without images')

    jpegs_for_news = prepare_jpegs_for_news(jpegs, mail_folder,
                                            os.path.join(mail_folder, IMG_FOR_NEWS_FOLDER))

    title, html = prepare_html_for_news(mail_metadata, mail_folder)
    return title, html, jpegs_for_news
