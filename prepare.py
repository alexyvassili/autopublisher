import os
import subprocess
import shutil
from bs4 import BeautifulSoup
from datetime import datetime
from razdel import sentenize

from document_utils import format_rasp_docx, cd, resize_jpeg_on_wide_size, docx2html, get_lines_from_html
from file_utils import format_jpeg_name, get_file_size_mb, get_files_for_extension, get_fullpath_files_for_extension

SOFFICE_PATH = "/opt/libreoffice6.3/program/soffice"
IMG_FOR_NEWS_FOLDER = 'img'
WIDE_SIDE_IMAGE = 1024
HTML_P_START = """<p style="text-align: justify; text-indent: 20px;"><span style="font-size: 14pt; line-height: 115%; font-family: 'Times New Roman', 'serif'; color: #000000;">"""
HTML_I_START = """<p style="text-align: justify; text-indent: 20px;"><span style="font-size: 12pt; line-height: 115%; font-family: 'Times New Roman', 'serif'; color: #000000;"><i>"""
HTML_P_END = '</span></p>'
HTML_I_END = '</i></span></p>'


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
    RASP_NAME = 'rasp_' + datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
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
        jpeg_fullname = os.path.join(folder, jpeg)
        size = get_file_size_mb(jpeg_fullname)
        new_jpeg = formatted_names_jpegs[jpeg]
        new_jpeg_fullname = os.path.join(jpegs_folder, new_jpeg)
        if size > 1.5:
            resize_jpeg_on_wide_size(jpeg_fullname, new_jpeg_fullname, WIDE_SIDE_IMAGE)
        else:
            shutil.copyfile(jpeg_fullname, new_jpeg_fullname)
        jpegs_for_news.append(new_jpeg_fullname)
    return jpegs_for_news


def prepare_html_for_news(mail_folder):
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


def prepare_text(text):
    try:
        title, news_text = text.split('\n', 1)
    except ValueError:
        # Если в тексте один абзац и нет заголовка,
        # вернем пустой тайтл, и возмем заголовок из заголовка письма на уровне выше
        title = ""
        news_text = text
    news_text = news_text.replace('\n', ' ')
    sentences = [i.text for i in sentenize(news_text)]
    return title, sentences


def html_from_sentences(sentences):
    paragraphs = []
    for line in sentences:
        if line.startswith("_"):
            # Письмо Кошелева от 25.08.2020:
            # В тексте новости приписка курсивом, который определился как
            # предложение, обрамленное подчеркиваниями.
            line = line.strip("_")
            paragraphs.append(f"{HTML_I_START}{line}{HTML_I_END}")
            continue
        paragraphs.append(f"{HTML_P_START}{line}{HTML_P_END}")
    return '\n'.join(paragraphs)


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
        string = string.replace('<p>', HTML_P_START)
        string = string.replace('</p>', HTML_P_END)
        paragraphs.append(string)
    news_html = '\n'.join(paragraphs)
    return title, news_html


def find_body_lines_in_fwd_mail(lines):
    message_body_flag = False
    body_lines = []
    for line in lines:
        if line.startswith('\\') or 'Конец пересылаемого сообщения' in line:
            message_body_flag = False
        if message_body_flag:
            body_lines.append(line)
        if '@' in line:
            message_body_flag = True
    return body_lines


def get_news_text_from_fwd_mail(html):
    lines = get_lines_from_html(html)
    body_lines = find_body_lines_in_fwd_mail(lines)
    text = '\n'.join(body_lines)
    if text.startswith('>'):
        text = text[2:]
    return text


def get_text_from_mail_body(metadata):
    if 'fwd' not in metadata['Subject'].lower():
        raise ValueError("Can't find text in non-forwarded messages")

    return get_news_text_from_fwd_mail(metadata['Body'])


def news(mail_folder):
    jpegs = get_files_for_extension(mail_folder, 'jpg') or get_files_for_extension(mail_folder, 'jpeg')
    if not jpegs:
        raise PrepareError('Can\'t publish news without images')

    jpegs_for_news = prepare_jpegs_for_news(jpegs, mail_folder,
                                            os.path.join(mail_folder, IMG_FOR_NEWS_FOLDER))

    title, html = prepare_html_for_news(mail_folder)
    return title, html, jpegs_for_news


def news_folder(mail_folder):
    """Prepare new materials from .doc or .zip/.rar
        or break execution"""
    extensions = ['jpeg', 'rar', 'zip', 'doc', 'docx']
    profiles = [{'jpeg': 'many', 'rar': 0, 'zip': 0, 'doc': 0, 'docx': 1},  # новость в docx
                {'jpeg': 'many', 'rar': 0, 'zip': 0, 'doc': 1, 'docx': 0},  # новость в doc
                {'jpeg': 'many', 'rar': 0, 'zip': 0, 'doc': 0, 'docx': 0},  # новость в теле письма
                {'jpeg': 0, 'rar': 1, 'zip': 0, 'doc': 0, 'docx': 0},  # новость в архиве rar
                {'jpeg': 0, 'rar': 0, 'zip': 1, 'doc': 0, 'docx': 0},  # новость в архиве zip
                ]
    counts = {}
    for ext in extensions:
        counts[ext] = get_files_for_extension(mail_folder, ext)
