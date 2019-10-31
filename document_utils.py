import os
import re
import shutil
import zipfile
import mammoth
import html2text
import xml.etree.ElementTree as ElementTree
from PIL import Image
from io import BytesIO
from subprocess import call

WORD_TMP_DIR = 'word_tmp'
FORMATTED_FILE = 'tmp_new_rasp.docx'

XML_NAME = os.path.join(WORD_TMP_DIR, 'word', 'document.xml')

OLD_FONT = "Izhitsa"
NEW_FONT = "Times New Roman"


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def unzip_without_structure(zip_name, folder):
    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        for member in zip_ref.namelist():
            filename = os.path.basename(member)
            # skip directories
            if not filename:
                continue

            # copy file (taken from zipfile's extract)
            with zip_ref.open(member) as source, open(os.path.join(folder, filename), "wb") as target:
                shutil.copyfileobj(source, target)


def unpack_docx(docx, folder):
    if os.path.exists(folder):
        raise ValueError(f'Folder {folder} is already exists')

    os.mkdir(folder)
    zip_ref = zipfile.ZipFile(docx, 'r')
    zip_ref.extractall(folder)
    zip_ref.close()


def replace_font_in_docx_xml(xml_name, old_font, new_font):
    with open(xml_name) as f:
        xml_string = f.read()

    if old_font not in xml_string:
        raise ValueError(f"Font {old_font} not fount in document")

    xml_string = xml_string.replace(old_font, new_font)

    with open(xml_name, 'w') as f:
        f.write(xml_string)


def add_cant_split_to_tr(tr: ElementTree.Element,  NS, NS_PREFIX):
    """Запрещает перенос строк на другую страницу в таблице в вордовском документе"""
    if tr.tag != f"{NS_PREFIX}tr":
        raise ValueError("Function add_cant_split get non-tr tag or broken NAMESPACE")
    trpr = tr.find('w:trPr', NS)
    if trpr is None:
        raise ValueError("Function add_cant_split can't find trPr element in tr")
    cantSplit = trpr.find('w:cantSplit', NS)
    if cantSplit is None:
        newCantSplit  = ElementTree.Element(f'{NS_PREFIX}cantSplit', {f'{NS_PREFIX}val': 'true'})
        trpr.append(newCantSplit)


def disable_table_split_in_docx_xml(xml_name):
    tree = ElementTree.parse(xml_name)
    root = tree.getroot()

    NAMESPACE = re.findall(r"\{(.*?)\}", root.tag)[0]
    NS = {'w': NAMESPACE, }
    NS_PREFIX = "{%s}" % NAMESPACE
    body = root.find('w:body', NS)
    table = body.find('w:tbl', NS)
    for tr in table.findall('w:tr', NS):
        add_cant_split_to_tr(tr, NS, NS_PREFIX)
    tree.write(xml_name)


def pack_docx(docx_name, folder_from):
    if not os.path.exists(folder_from):
        raise ValueError(f"Cant't found docx folder: {folder_from}")
    if os.path.exists(docx_name):
        raise ValueError(f"Docx file is already exists: {docx_name}")

    zipf = zipfile.ZipFile(docx_name, 'w', zipfile.ZIP_DEFLATED)
    with cd(folder_from):
        for item in os.listdir('.'):
            if not os.path.isfile(os.path.join(item)):
                zipdir(item, zipf)
            else:
                zipf.write(item)
    zipf.close()


def format_rasp_docx(docx, mail_folder):
    unpack_docx(os.path.join(mail_folder, docx), os.path.join(mail_folder, WORD_TMP_DIR))
    xml_full_name = os.path.join(mail_folder, XML_NAME)
    formatted_filename = os.path.join(mail_folder, FORMATTED_FILE)
    replace_font_in_docx_xml(xml_full_name, OLD_FONT, NEW_FONT)
    disable_table_split_in_docx_xml(xml_full_name)
    pack_docx(formatted_filename, os.path.join(mail_folder, WORD_TMP_DIR))
    shutil.rmtree(os.path.join(mail_folder, WORD_TMP_DIR))
    return formatted_filename


def get_image_size(image_filename):
    with open(image_filename, 'rb') as f:
        image_file = BytesIO(f.read())
    image = Image.open(image_file)
    width, height = image.size
    return width, height


def get_resized_image_size(width, height, wide_side):
    wide = max(width, height)
    coef = wide / wide_side
    return int(width/coef), int(height/coef)


def resize_jpeg_on_wide_size(jpeg, new_jpeg, wide_side_size):
    """Ресайз картинки с определенным размером по широкой стороне"""
    width, height = get_image_size(jpeg)
    m_width, m_height = get_resized_image_size(width, height, wide_side=wide_side_size)

    call(["convert", jpeg, "-resize", str(m_width), "-quality", "100", new_jpeg])


def docx2html(docx):
    with open(docx, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value  # The generated HTML
        messages = result.messages  # Any messages, such as warnings during conversion
    return html, messages


def get_text_from_html(html):
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.bypass_tables = True
    h.blockquote = -1
    h.strong_mark = ""
    text = h.handle(html)
    # убираем идущие подряд переносы строк
    # и строки, состоящие из одних пробелов
    text = '\n'.join(t for t in text.split('\n')
                     if t and not re.match(r'^\s+$', t))
    return text
