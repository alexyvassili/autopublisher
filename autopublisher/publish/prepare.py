import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from razdel import sentenize

from autopublisher.config import IMAGEMAGICK_PATH, SOFFICE_PATH, config
from autopublisher.documents.document import (
    HtmlT,
    cd,
    docx2html,
    format_rasp_docx,
    get_lines_from_html,
    resize_jpeg_on_wide_size,
)
from autopublisher.documents.image import Image
from autopublisher.utils.dt import get_dt_now_string
from autopublisher.utils.file import (
    format_img_name,
    get_file_size_mb,
    get_files_for_extension,
)


log = logging.getLogger(__name__)


IMG_FOR_NEWS_FOLDER = "img"
WIDE_SIDE_IMAGE = 1024
MAX_NEWS_IMAGE_SIZE_MB = 1.5

HTML_P_START = """<p style="text-align: justify; text-indent: 20px;"><span style="font-size: 14pt; line-height: 115%; font-family: 'Times New Roman', 'serif'; color: #000000;">"""  # noqa:E501
HTML_P_END = "</span></p>"


class PrepareError(Exception):
    pass


def check_rasp_folder(folder: Path) -> None:
    log.info("Check folder %s", folder)
    docxs = [item for item in folder.iterdir() if item.suffix == ".docx"]
    if not docxs:
        raise PrepareError("Can't find word file in mail")
    if len(docxs) > 1:
        raise PrepareError("Too many word files in mail")

    images = []
    for ext in (".jpg", ".png"):
        images += get_files_for_extension(folder, ext)

    if images:
        raise PrepareError("Jpeg or png in rasp mail found!")


def rasp(mail_folder: Path) -> list[Path]:
    rasp_img_name = "rasp_" + get_dt_now_string()
    rasp_img_name = f"{rasp_img_name}.{config.rasp_image_format}"
    rasp_img_path = mail_folder / rasp_img_name

    # rasp folder must contain only one .docx and no jpegs
    check_rasp_folder(mail_folder)

    docxs = get_files_for_extension(mail_folder, ".docx")
    docx_name = docxs[0]
    formatted_docx = format_rasp_docx(docx_name, mail_folder)

    if not formatted_docx.exists():
        raise PrepareError(f"Can't find formatted docx: {formatted_docx}")

    with cd(mail_folder):
        soffice_command = [
            SOFFICE_PATH,
            "--headless",
            "--convert-to", "pdf",
            str(formatted_docx),
        ]
        log.info("RUN: %s", " ".join(soffice_command))
        subprocess.call(soffice_command)  # noqa:S603
        pdf_name = mail_folder / f"{formatted_docx.stem}.pdf"
        if not pdf_name.exists():
            raise PrepareError(
                f"Can't find formatted pdf: {formatted_docx}",
            )

        # previous version of this command:
        # ["convert", "-density", "300", PDF_NAME, "-quality", "100", JPG_NAME]  # noqa:ERA001,E501
        imagemagick_command = [
            IMAGEMAGICK_PATH,
            "-verbose",
            "-density", "150",
            # add "-trim", to remove page fields
            str(pdf_name),
            "-quality", "100",
            "-alpha", "remove",
            # add "-sharpen", "0x1.0", to more image sharpness
            "-colorspace", "sRGB",
            str(rasp_img_path),
        ]
        log.info("RUN: %s", " ".join(imagemagick_command))
        subprocess.call(imagemagick_command)  # noqa:S603
    rasp_images = get_files_for_extension(
        mail_folder, config.rasp_image_format,
    )
    rasp_images.sort()
    log.info("Rasp images: %s", ", ".join(map(str, rasp_images)))

    if not rasp_images:
        raise PrepareError("Can't find rasp images")

    return rasp_images


def prepare_jpegs_for_news(
        *, jpegs: list[Path], jpegs_folder: Path,
) -> list[Path]:
    """jpegs: full-path jpegs"""
    jpegs_for_news = []
    jpegs_folder.mkdir(parents=True)
    formatted_names_jpegs = {
        jpeg: format_img_name(jpeg.name) for jpeg in jpegs
    }
    for jpeg in jpegs:
        size = get_file_size_mb(jpeg)
        new_jpeg = jpegs_folder / formatted_names_jpegs[jpeg]
        if size > MAX_NEWS_IMAGE_SIZE_MB:
            resize_jpeg_on_wide_size(
                jpeg, new_jpeg, WIDE_SIDE_IMAGE,
            )
        else:
            shutil.copyfile(jpeg, new_jpeg)
        jpegs_for_news.append(new_jpeg)
    return jpegs_for_news


def prepare_mainpage_jpeg(image: Image) -> None:
    # TODO: Unused function
    size = get_file_size_mb(image.path)

    if size > 1:
        logging.info("Mainpage image size is greater then 1 MB, resizing...")
        tmp_image_path = image.folder / "resized.jpg"
        resize_jpeg_on_wide_size(image.path, tmp_image_path, WIDE_SIDE_IMAGE)
        shutil.move(tmp_image_path, image.path)


def prepare_html_for_news(mail_folder: Path) -> tuple[str, HtmlT]:
    docxs = get_files_for_extension(mail_folder, ".docx")
    if not docxs:
        raise PrepareError("Can't search news text in mail body")
    if len(docxs) > 1:
        raise PrepareError("Found many docx for one news")
    docx = docxs[0]
    title, html = get_html_news_from_docx(docx)
    return title, html


def prepare_text(text: str) -> tuple[str, list[str]]:
    try:
        title, news_text = text.split("\n", 1)
    except ValueError:
        # Если в тексте один абзац и нет заголовка,
        # вернем пустой тайтл, и возмем заголовок
        # из заголовка письма на уровне выше
        title = ""
        news_text = text
    news_text = news_text.replace("\n", " ")
    sentences = [i.text for i in sentenize(news_text)]
    return title, sentences


def html_from_sentences(sentences: list[str]) -> HtmlT:
    paragraphs = [
        f"{HTML_P_START}{line}{HTML_P_END}"
        for line in sentences
    ]
    return "\n".join(paragraphs)


def get_html_news_from_docx(docx: Path) -> tuple[str, HtmlT]:
    html, messages = docx2html(docx)
    soup = BeautifulSoup(html, "html.parser")
    paragraphs: list[str] = []
    title = None
    for p in soup.find_all("p"):
        string_p = str(p)
        if not title:
            title = p.text
            continue
        string_p = string_p.replace("<p>", HTML_P_START)
        string_p = string_p.replace("</p>", HTML_P_END)
        paragraphs.append(string_p)
    news_html = "\n".join(paragraphs)
    return title, news_html  # type: ignore[return-value]


def find_body_lines_in_fwd_mail(lines: list[str]) -> list[str]:
    message_body_flag = False
    body_lines = []
    for line in lines:
        if line.startswith("\\") or "Конец пересылаемого сообщения" in line:
            message_body_flag = False
        if message_body_flag:
            body_lines.append(line)
        if "@" in line:
            message_body_flag = True
    return body_lines


def get_news_text_from_fwd_mail(html: HtmlT) -> str:
    lines = get_lines_from_html(html)
    body_lines = find_body_lines_in_fwd_mail(lines)
    text = "\n".join(body_lines)
    if text.startswith(">"):
        text = text[2:]
    return text


def get_text_from_mail_body(metadata: dict[str, Any]) -> str:
    if "fwd" not in metadata["Subject"].lower():
        raise ValueError("Can't find text in non-forwarded messages")

    return get_news_text_from_fwd_mail(metadata["Body"])
