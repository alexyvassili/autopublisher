import os
import re
import shutil
import mail
import html2text

from settings import TMP_FOLDER, TMP_FOLDER_PREFIX


class CurrentMail:
    def __init__(self):
        self.mail_id = None
        self.folder = None
        self.metadata = None
        self.text = None
        self.about = None

    def init_mail(self, mail_id, mail_folder, mail_metadata):
        self.mail_id = mail_id
        self.folder = mail_folder
        self.metadata = mail_metadata
        self.text = get_mail_text(mail_metadata['Body'])
        self.about = get_mail_about(mail_metadata, self.text)

    def rollback(self):
        if self.mail_id:
            mark_mail_as_unread(self.mail_id)
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()


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


def get_mail_text(html):
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
