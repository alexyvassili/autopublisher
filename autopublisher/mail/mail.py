import os
import logging
import imaplib
import email
from email.header import decode_header
import mimetypes
import shutil

from secrets import MAIL_SERVER, MAIL_LOGIN, MAIL_PASSWORD


def get_connection():
    imap = imaplib.IMAP4_SSL(MAIL_SERVER)
    status, response = imap.login(MAIL_LOGIN, MAIL_PASSWORD)
    if status != 'OK':
        raise ConnectionError(f"Error logged in email box. Status: {status}")
    imap.select('INBOX')
    return imap


def get_new_mails_from(connection, from_email):
    status, new_mails_ids = connection.search(None, f'(FROM {from_email} UNSEEN)')
    new_mails_ids = [uid for uid in new_mails_ids[0].split(b' ') if uid]
    return new_mails_ids


def decode_mail_field(message, field):
    try:
        data, encoding = decode_header(message[field])[0]
    except TypeError:
        return ""
    if encoding:
        data = data.decode(encoding)
    return data


def get_attachments_list(message):
    attachments = []
    for part in message.walk():
        if part.get_content_maintype() == 'multipart':
            continue

        filename = part.get_filename()
        if filename:
            bts, encoding = decode_header(filename)[0]
            if encoding:
                filename = bts.decode(encoding)

            attachments.append(filename)
    return attachments


def get_mail_metadata(message):
    mail_metadata = {}
    mail_metadata['Date'] = message['Date']
    mail_metadata['From'] = decode_mail_field(message, 'From')
    mail_metadata['Subject'] = decode_mail_field(message, 'Subject')
    try:
        # get_payload can return list or bytes str, so
        # try with str raise AttributeError: 'str' object has no attribute 'get_payload'
        mail_body = message.get_payload()[0].get_payload(decode=True)
    except AttributeError:
        mail_body = message.get_payload(decode=True)
    mail_metadata['Body'] = mail_body.decode()
    mail_metadata['Attachments'] = get_attachments_list(message)
    return mail_metadata


def get_message(connection, mail_id):
    response, mail_binary_data = connection.fetch(mail_id, '(RFC822)')
    assert response == "OK"
    message = email.message_from_bytes(mail_binary_data[0][1])
    return message


def save_email(message, mail_folder):
    if os.path.exists(mail_folder):
        shutil.rmtree(mail_folder)

    os.makedirs(mail_folder)

    # The code below was copied from example
    counter = 1
    for part in message.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue
        # Applications should really sanitize the given filename so that an
        # email message can't be used to overwrite important files
        filename = part.get_filename()
        if not filename:
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                # Use a generic bag-of-bits extension
                ext = '.bin'
            filename = 'part-%03d%s' % (counter, ext)
        else:
            bts, encoding = decode_header(filename)[0]
            if encoding:
                filename = bts.decode(encoding)
        counter += 1
        with open(os.path.join(mail_folder, filename), 'wb') as fp:
            # Сломано письмом Кошелева от 3 марта 2020
            # во вложениях неопознанный .txt (читается)
            # и неопознанный .eml (!) (ну это результат mimetypes.guess_extension см. выше)
            # на этом .eml get_payload возвращает None и все ломается.
            # в принципе, нам это не нужно, но само явление любопытное
            # FIX: оборачиваем в ексепшн и создаем пустой файл
            try:
                fp.write(part.get_payload(decode=True))
            except TypeError:
                logging.warning(f"Сохранение {filename} не удалось: получен не строковый объект.")
                fp.write(b"\n")


def mark_as_unread(connection, mail_id: bytes):
    connection.store(mail_id, '-FLAGS', '(\Seen)')


def close_connection(connection):
    status, response = connection.logout()
    if status != 'BYE':
        raise ConnectionError(f"Error logged out email box. Status: {status}")
