import os
import logging
import shutil
import mail
import prepare
from document_utils import docx2html, get_text_from_html
from spelling import spell_line

from settings import TMP_FOLDER, TMP_FOLDER_PREFIX


class CurrentMail:
    def __init__(self):
        self.mail_id = None
        self.folder = None
        self.metadata = None
        self.text = None
        self.title = None
        self.sentences = None
        self.text_ready = None
        self.images = None
        self.about = None

    def init_mail(self, mail_id, mail_folder, mail_metadata):
        self.mail_id = mail_id
        self.folder = mail_folder
        self.metadata = mail_metadata
        self.text = get_text_from_html(mail_metadata['Body'])
        self.about = get_mail_about(mail_metadata, self.text)

    def clear(self):
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()

    def rollback(self):
        if self.mail_id:
            mark_mail_as_unread(self.mail_id)
        self.clear()


def load_one_mail_rollback(mail_id, mail_folder):
    connection = mail.get_connection()
    mail.mark_as_unread(connection, mail_id)
    mail.close_connection(connection)
    shutil.rmtree(mail_folder)


def load_most_old_mail_from(mail_from):
    mail_id, mail_folder, mail_metadata = None, None, None
    connection = mail.get_connection()
    try:
        new_mails_ids = mail.get_new_mails_from(connection, mail_from)
        if new_mails_ids:
            mail_id = new_mails_ids[0]
            mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + mail_id.decode())
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
    body = body_text or mail_metadata['Body']

    about = f"""{mail_metadata['Date']}
Subject: {mail_metadata['Subject']}

{body}

Attachments:
"""
    for i, att in enumerate(mail_metadata['Attachments']):
        about += f"{i+1}) {att}\n"
    return about


def get_text_from_docx(docx):
    html, messages = docx2html(docx)
    text = get_text_from_html(html)
    return text


def get_text_for_news(current_mail):
    docxs = prepare.get_fullpath_files_for_extension(current_mail.folder, 'docx')
    if not docxs:
        text = prepare.get_text_from_mail_body(current_mail.metadata)
    elif len(docxs) > 1:
        raise prepare.PrepareError("Found many docx for one news")
    else:
        docx = docxs[0]
        text = get_text_from_docx(docx)
    title, sentences = prepare.prepare_text(text)
    title = spell_line(title)
    try:
        spelled_sentences = [spell_line(sent) for sent in sentences]
    except Exception as e:
        logging.warning("Error in spellchecker")
        spelled_sentences = sentences
    return title, spelled_sentences


def get_images_for_news(current_mail):
    jpegs = (prepare.get_files_for_extension(current_mail.folder, 'jpg') +
             prepare.get_files_for_extension(current_mail.folder, 'jpeg'))
    if not jpegs:
        return []

    jpegs_for_news = prepare.prepare_jpegs_for_news(jpegs, current_mail.folder,
                                            os.path.join(current_mail.folder, prepare.IMG_FOR_NEWS_FOLDER))
    return jpegs_for_news
