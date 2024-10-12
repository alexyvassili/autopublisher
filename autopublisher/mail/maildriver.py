import logging
import os
import shutil
from pathlib import Path
from typing import Any

from autopublisher.config import config
from autopublisher.mail import mail
from autopublisher.publish import prepare
from autopublisher.documents.document import (
    docx2html,
    get_text_from_html,
    unrar,
    unzip_without_structure,
)
from autopublisher.utils.spelling import spell_line


log = logging.getLogger(__name__)


class CurrentMail:
    def __init__(
            self, *,
            mail_id: str,
            mail_folder: Path,
            mail_metadata: dict[str, Any],
    ):
        self.mail_id: str = mail_id
        self.folder: Path = mail_folder
        self.metadata: dict[str, Any] = mail_metadata
        self.text: str = get_text_from_html(mail_metadata["Body"])
        self.about: str = get_mail_about(mail_metadata, self.text)
        self.attachments: list[str] = self.metadata["Attachments"]
        self.title: str | None = None
        self.sentences: list[str] | None = None
        self.images: list[Path] | None = None
        self._prepare_attachments()

    def _prepare_attachments(self) -> None:
        if len(self.attachments) != 1:
            return

        if self.attachments[0].endswith(".zip"):
            unzip_without_structure(
                self.folder / self.attachments[0], self.folder,
            )
        elif self.attachments[0].endswith(".rar"):
            self.about += f"\nUnpack {self.attachments[0]} to {self.folder}\n"
            response = unrar(
                self.folder / self.attachments[0], self.folder,
            )
            self.about += f"{response}\n"
        else:
            return
        self._add_attachments_to_about()

    def _add_attachments_to_about(self) -> None:
        self.about += "\nUnpacked Attachments:\n"
        attach_files = [
            f for f in self.folder.iterdir()
            if (self.folder / f).is_file()
        ]
        for i, att in enumerate(attach_files):
            self.about += f"{i+1}) {att}\n"

    def clear(self) -> None:
        if self.folder:
            shutil.rmtree(self.folder)

    def rollback(self) -> None:
        if self.mail_id:
            mark_mail_as_unread(self.mail_id)
        self.clear()


def load_one_mail_rollback(mail_id: str, mail_folder: Path) -> None:
    connection = mail.get_connection()
    mail.mark_as_unread(connection, mail_id)
    mail.close_connection(connection)
    shutil.rmtree(mail_folder)


def load_most_old_mail_from(
        mail_from: str,
) -> tuple[str, Path, dict[str, Any]]:
    mail_id, mail_folder, mail_metadata = None, None, None
    log.info("Connecting to mail server...")
    connection = mail.get_connection()
    try:
        log.info("Success, load new mails...")
        new_mails_ids = mail.get_new_mails_from(connection, mail_from)
        if new_mails_ids:
            mail_id = new_mails_ids[0]
            mail_folder_name = config.tmp_folder_prefix + mail_id
            mail_folder = config.tmp_folder / mail_folder_name
            message = mail.get_message(connection, mail_id)
            mail_metadata = mail.get_mail_metadata(message)
            mail.save_email(message, mail_folder)
    except Exception:
        if mail_id:
            mail.mark_as_unread(connection, mail_id)
        raise

    finally:
        mail.close_connection(connection)

    return mail_id, mail_folder, mail_metadata


def mark_mail_as_unread(mail_id: str) -> None:
    connection = mail.get_connection()
    try:
        if mail_id:
            mail.mark_as_unread(connection, mail_id)
    finally:
        mail.close_connection(connection)


def get_mail_about(
        mail_metadata: dict[str, Any], body_text: str | None = None,
) -> str:
    body = body_text or mail_metadata["Body"]

    about = f"""{mail_metadata["Date"]}
Subject: {mail_metadata["Subject"]}

{body}

Attachments:
"""
    for i, att in enumerate(mail_metadata["Attachments"]):
        about += f"{i+1}) {att}\n"
    return about


def get_text_from_docx(docx: Path) -> str:
    html, messages = docx2html(docx)
    return get_text_from_html(html)


def get_text_for_news(mail: CurrentMail) -> tuple[str, list[str]]:
    docxs = prepare.get_files_for_extension(mail.folder, ".docx")
    if not docxs:
        text = prepare.get_text_from_mail_body(mail.metadata)
    elif len(docxs) > 1:
        raise prepare.PrepareError("Found many docx for one news")
    else:
        docx = docxs[0]
        text = get_text_from_docx(docx)
    # Сломано письмом Кошелева от 29.01.2020
    # Причина: тело письма не содержит заголовка новости,
    # заголовок новости только в заголовке письма.
    # Решение: пока не меняем диалог, просто возьмем
    # заголовок из заголовка письма.
    title, sentences = prepare.prepare_text(text)
    if not title:
        title = mail.metadata["Subject"] or "Новость"

    if "Fwd: " in title:
        title = title.split("Fwd: ")[1]

    title = spell_line(title)
    try:
        spelled_sentences = [spell_line(sent) for sent in sentences]
    except Exception:
        logging.warning("Error in spellchecker")
        spelled_sentences = sentences
    return title, spelled_sentences


def get_images_for_news(mail: CurrentMail) -> list[Path]:
    jpegs = prepare.get_files_for_extension(mail.folder, ".jpg") + \
            prepare.get_files_for_extension(mail.folder, ".jpeg")
    if not jpegs:
        return []

    jpegs_for_news = prepare.prepare_jpegs_for_news(
        jpegs=jpegs,
        jpegs_folder=mail.folder / prepare.IMG_FOR_NEWS_FOLDER,
    )
    return jpegs_for_news  # noqa:RET504
