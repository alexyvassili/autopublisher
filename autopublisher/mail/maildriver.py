import os
import logging
import shutil
from pathlib import Path

from autopublisher.config import config
import autopublisher.mail.mail as mail
import autopublisher.publish.prepare as prepare
from autopublisher.utils.document import (
    docx2html, get_text_from_html, unzip_without_structure, unrar
)
from autopublisher.utils.spelling import spell_line


log = logging.getLogger(__name__)


class CurrentMail:
    def __init__(self):
        self.mail_id = None
        self.folder: Path | None = None
        self.metadata = None
        self.text = None
        self.title = None
        self.sentences = None
        self.text_ready = None
        self.images = None
        self.about = None

    def init_mail(self, mail_id, mail_folder: Path, mail_metadata):
        self.mail_id = mail_id
        self.folder = mail_folder
        self.metadata = mail_metadata
        self.text = get_text_from_html(mail_metadata["Body"])
        self.about = get_mail_about(mail_metadata, self.text)
        self.attachments = self.metadata["Attachments"]
        self.prepare()

    def clear(self):
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()

    def rollback(self):
        if self.mail_id:
            mark_mail_as_unread(self.mail_id)
        self.clear()

    def prepare(self):
        if len(self.attachments) == 1 and \
                self.attachments[0].endswith(".zip"):
            unzip_without_structure(
                os.path.join(self.folder, self.attachments[0]), self.folder
            )
        elif len(self.attachments) == 1 and \
                self.attachments[0].endswith(".rar"):
            self.about += f"\nUnpack {self.attachments[0]} to {self.folder}\n"
            response = unrar(
                os.path.join(self.folder, self.attachments[0]), self.folder
            )
            self.about += f"{response}\n"
        else:
            return
        self.update_about()

    def update_about(self):
        self.about += "\nUnpacked Attachments:\n"
        attach_files = [
            f for f in os.listdir(self.folder)
            if os.path.isfile(os.path.join(self.folder, f))
        ]
        for i, att in enumerate(attach_files):
            self.about += f"{i+1}) {att}\n"


def load_one_mail_rollback(mail_id, mail_folder):
    connection = mail.get_connection()
    mail.mark_as_unread(connection, mail_id)
    mail.close_connection(connection)
    shutil.rmtree(mail_folder)


def load_most_old_mail_from(mail_from):
    mail_id, mail_folder, mail_metadata = None, None, None
    log.info("Connecting to mail server...")
    connection = mail.get_connection()
    try:
        log.info("Success, load new mails...")
        new_mails_ids = mail.get_new_mails_from(connection, mail_from)
        if new_mails_ids:
            mail_id = new_mails_ids[0]
            mail_folder_name = config.tmp_folder_prefix + mail_id.decode()
            mail_folder = config.tmp_folder / mail_folder_name
            message = mail.get_message(connection, mail_id)
            mail_metadata = mail.get_mail_metadata(message)
            mail.save_email(message, mail_folder)
    except Exception as e:
        if mail_id:
            mail.mark_as_unread(connection, mail_id)
        raise e

    finally:
        mail.close_connection(connection)

    return mail_id, mail_folder, mail_metadata


def mark_mail_as_unread(mail_id):
    connection = mail.get_connection()
    try:
        if mail_id:
            mail.mark_as_unread(connection, mail_id)
    finally:
        mail.close_connection(connection)


def get_mail_about(mail_metadata, body_text=None):
    body = body_text or mail_metadata["Body"]

    about = f"""{mail_metadata["Date"]}
Subject: {mail_metadata["Subject"]}

{body}

Attachments:
"""
    for i, att in enumerate(mail_metadata["Attachments"]):
        about += f"{i+1}) {att}\n"
    return about


def get_text_from_docx(docx):
    html, messages = docx2html(docx)
    text = get_text_from_html(html)
    return text


def get_text_for_news(current_mail):
    docxs = prepare.get_fullpath_files_for_extension(
        current_mail.folder, "docx",
    )
    if not docxs:
        text = prepare.get_text_from_mail_body(current_mail.metadata)
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
        title = current_mail.metadata["Subject"] or "Новость"

    if "Fwd: " in title:
        title = title.split("Fwd: ")[1]

    title = spell_line(title)
    try:
        spelled_sentences = [spell_line(sent) for sent in sentences]
    except Exception as e:
        logging.warning("Error in spellchecker")
        spelled_sentences = sentences
    return title, spelled_sentences


def get_images_for_news(current_mail):
    jpegs = (prepare.get_files_for_extension(current_mail.folder, "jpg") +
             prepare.get_files_for_extension(current_mail.folder, "jpeg"))
    if not jpegs:
        return []

    jpegs_for_news = prepare.prepare_jpegs_for_news(
        jpegs,
        current_mail.folder,
        # TODO: переделать всё на pathlib
        os.path.join(current_mail.folder, prepare.IMG_FOR_NEWS_FOLDER)
    )
    return jpegs_for_news
