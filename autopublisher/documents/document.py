import logging
import os
import re
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from subprocess import PIPE, Popen, call
from types import TracebackType
from xml.etree import ElementTree

import html2text
import mammoth
from PIL import Image

from autopublisher.config import IMAGEMAGICK_PATH


WORD_TMP_DIR = Path("word_tmp")
FORMATTED_FILE = "tmp_new_rasp.docx"

XML_NAME = WORD_TMP_DIR / "word" / "document.xml"

OLD_FONT = "Izhitsa"
NEW_FONT = "Times New Roman"


HtmlT = str


class cd:  # noqa:N801
    """Context manager for changing the current working directory"""
    def __init__(self, new_path: Path):
        self.new_path = new_path.expanduser()

    def __enter__(self) -> None:
        self.saved_path: Path = Path.cwd()
        os.chdir(self.new_path)

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            value: BaseException | None,
            traceback: TracebackType | None,
    ) -> None:
        os.chdir(self.saved_path)


def zipdir(path: Path, ziph: zipfile.ZipFile) -> None:
    # ziph is zipfile handle
    for root, _dirs, files in os.walk(path):
        for file in files:
            ziph.write(Path(root) / file)


def unzip_without_structure(zip_name: Path, folder: Path) -> None:
    with zipfile.ZipFile(zip_name, "r") as zip_ref:
        for member in zip_ref.namelist():
            filename = Path(member).name
            # skip directories
            if not filename:
                continue

            # copy file (taken from zipfile's extract)
            with (
                zip_ref.open(member) as source,
                (folder / filename).open("wb") as target,
            ):
                shutil.copyfileobj(source, target)


def unpack_docx(docx: Path, folder: Path) -> None:
    if folder.exists():
        raise ValueError(f"Folder {folder} is already exists")

    folder.mkdir(parents=True)
    zip_ref = zipfile.ZipFile(docx, "r")
    zip_ref.extractall(folder)
    zip_ref.close()


def replace_font_in_docx_xml(
        xml_name: Path, old_font: str, new_font: str,
) -> None:
    with xml_name.open() as f:
        xml_string = f.read()

    if old_font not in xml_string:
        raise ValueError(f"Font {old_font} not fount in document")

    xml_string = xml_string.replace(old_font, new_font)

    with xml_name.open("w") as f:
        f.write(xml_string)


def add_cant_split_to_tr(
        tr: ElementTree.Element,
        NS: dict[str, str],  # noqa:N803
        NS_PREFIX: str,  # noqa:N803
) -> None:
    """Запрещает перенос строк на другую страницу
       в таблице в вордовском документе
    """
    if tr.tag != f"{NS_PREFIX}tr":
        raise ValueError(
            "Function add_cant_split get non-tr tag or broken NAMESPACE",
        )
    trpr = tr.find("w:trPr", NS)
    if trpr is None:
        logging.warning(
            "Function add_cant_split can't find trPr element in tr",
        )
        trpr = ElementTree.Element("{%s}trPr" % NS["w"])
        tr.append(trpr)
    cant_split = trpr.find("w:cantSplit", NS)
    if cant_split is None:
        new_cant_split = ElementTree.Element(
            f"{NS_PREFIX}cantSplit", {f"{NS_PREFIX}val": "true"},
        )
        trpr.append(new_cant_split)


def disable_table_split_in_docx_xml(xml_name: Path) -> None:
    tree = ElementTree.parse(xml_name)
    root = tree.getroot()

    NAMESPACE = re.findall(r"\{(.*?)\}", root.tag)[0]  # noqa: N806
    NS = {"w": NAMESPACE}  # noqa: N806
    NS_PREFIX = "{%s}" % NAMESPACE  # noqa: N806
    body = root.find("w:body", NS)
    table = body.find("w:tbl", NS)  # type: ignore[union-attr]
    for tr in table.findall("w:tr", NS):  # type: ignore[union-attr]
        add_cant_split_to_tr(tr, NS, NS_PREFIX)
    tree.write(xml_name)


def pack_docx(docx_name: Path, folder_from: Path) -> None:
    if not folder_from.exists():
        raise ValueError(f"Can't found docx folder: {folder_from}")
    if docx_name.exists():
        raise ValueError(f"Docx file is already exists: {docx_name}")

    zipf = zipfile.ZipFile(docx_name, "w", zipfile.ZIP_DEFLATED)
    with cd(folder_from):
        for item in Path().iterdir():
            if not item.is_file():
                zipdir(item, zipf)
            else:
                zipf.write(item)
    zipf.close()


def format_rasp_docx(docx: Path, mail_folder: Path) -> Path:
    word_tmp_dir = mail_folder / WORD_TMP_DIR
    unpack_docx(docx, word_tmp_dir)
    xml_full_name = mail_folder / XML_NAME
    formatted_filename = mail_folder / FORMATTED_FILE
    replace_font_in_docx_xml(xml_full_name, OLD_FONT, NEW_FONT)
    disable_table_split_in_docx_xml(xml_full_name)
    pack_docx(formatted_filename, word_tmp_dir)
    shutil.rmtree(word_tmp_dir)
    return formatted_filename


def get_image_size(image_filename: Path) -> tuple[int, int]:
    with image_filename.open("rb") as f:
        image_file = BytesIO(f.read())
    image = Image.open(image_file)
    width, height = image.size
    return width, height


def get_resized_image_size(
        width: int, height: int, wide_side: int,
) -> tuple[int, int]:
    wide = max(width, height)
    coef = wide / wide_side
    return int(width / coef), int(height / coef)


def resize_jpeg_on_wide_size(
        jpeg: Path, new_jpeg: Path, wide_side_size: int,
) -> None:
    """Ресайз картинки с определенным размером по широкой стороне.
    Пример bash-команды для аналогичной задачи:
    `for jpeg in *.jpg; do convert $jpeg -resize 1024 -quality 100 \
     $(echo ${jpeg%%.*}_1.jpg); done`
    """
    width, height = get_image_size(jpeg)
    m_width, m_height = get_resized_image_size(
        width, height, wide_side=wide_side_size,
    )

    call([  # noqa:S603 (check for execution of untrusted input)
        IMAGEMAGICK_PATH,
        str(jpeg),
        "-resize", str(m_width),
        "-quality", "100",
        str(new_jpeg),
    ])


def docx2html(docx: Path) -> tuple[HtmlT, list[str]]:
    with docx.open("rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        # The generated HTML
        html = result.value
        # Any messages, such as warnings during conversion
        messages = result.messages
    return html, messages


def get_lines_from_html(html: HtmlT) -> list[str]:
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.bypass_tables = True
    h.blockquote = -1
    h.strong_mark = ""
    text = h.handle(html)
    # html2text вставляет внутри абзацев переносы строк (видимо, для красоты),
    # а сами абзацы отделяет четырьмя переносами строк
    # поэтому разбиваем текст на абзацы,
    # а переносы строк внутри абзацев убираем.
    return [
        line.strip().replace("\n", " ")
        for line in re.split(r"\n{2,}", text)
        if line and not re.match(r"^\s+$", line)
    ]


def get_text_from_html(html: HtmlT) -> str:
    lines = get_lines_from_html(html)
    return "\n".join(lines)


def unrar(rarfile: Path, folder: Path) -> str:
    # TODO: переписать на новое API subprocess
    p = Popen(
        ["/usr/bin/unrar", "x", str(rarfile), str(folder)],  # noqa: S603
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    output, err = p.communicate()
    rc = p.returncode
    output = output.decode()
    err = err.decode()
    return f"Output: \n{output}\nErrors: \n{err}\nReturn Code: {rc}"
