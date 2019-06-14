import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ElementTree

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
