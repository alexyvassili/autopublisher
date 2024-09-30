import email
import imaplib
import logging
import mimetypes
import shutil
from email.header import decode_header
from pathlib import Path
from typing import Any

from autopublisher.config import config


# TODO: сделать MailClient
def get_connection() -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL(config.mail_server)
    status, response = imap.login(config.mail_login, config.mail_passwd)
    if status != "OK":
        raise ConnectionError(f"Error logged in email box. Status: {status}")
    imap.select("INBOX")
    return imap


def get_new_mails_from(
        connection: imaplib.IMAP4_SSL,
        from_email: str,
) -> list[str]:
    status, unseen_mails = connection.search(
        None, f"(FROM {from_email} UNSEEN)",
    )
    new_mails_ids = [
        uid for uid in unseen_mails[0].decode().split(" ") if uid
    ]
    return new_mails_ids  # noqa:RET504


def decode_mail_field(message: email.message.Message, field: str) -> str:
    try:
        data, encoding = decode_header(message[field])[0]
    except TypeError:
        return ""
    if encoding:
        data = data.decode(encoding)
    return data


def get_attachments_list(message: email.message.Message) -> list[str]:
    attachments = []
    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue

        filename = part.get_filename()
        if filename:
            bts, encoding = decode_header(filename)[0]
            if encoding:
                filename = bts.decode(encoding)

            attachments.append(filename)
    return attachments


def get_mail_metadata(message: email.message.Message) -> dict[str, Any]:
    mail_metadata = {
        "Date": message["Date"],
        "From": decode_mail_field(message, "From"),
        "Subject": decode_mail_field(message, "Subject"),
    }
    try:
        # get_payload can return list or bytes str, so
        # try with str raise AttributeError:
        # "str" object has no attribute "get_payload"
        mail_body = message.get_payload()[0].get_payload(decode=True)
    except AttributeError:
        mail_body = message.get_payload(decode=True)
    mail_metadata["Body"] = mail_body.decode() if mail_body else ""
    mail_metadata["Attachments"] = get_attachments_list(message)
    return mail_metadata


def get_message(
        connection: imaplib.IMAP4_SSL,
        mail_id: str,
) -> email.message.Message:
    # TODO: добавить retry
    response, mail_binary_data = connection.fetch(mail_id, "(RFC822)")
    if response != "OK":
        raise ValueError(f"Response status is not OK: `{response}`")
    return email.message_from_bytes(mail_binary_data[0][1])


def save_email(message: email.message.Message, mail_folder: Path) -> None:
    if mail_folder.exists():
        shutil.rmtree(mail_folder)

    mail_folder.mkdir(parents=True)

    # The code below was copied from example
    counter = 1
    for part in message.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == "multipart":
            continue
        # Applications should really sanitize the given filename so that an
        # email message can't be used to overwrite important files
        filename = part.get_filename()
        if not filename:
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                # Use a generic bag-of-bits extension
                ext = ".bin"
            filename = "part-%03d%s" % (counter, ext)
        else:
            bts, encoding = decode_header(filename)[0]
            if encoding:
                filename = bts.decode(encoding)
        counter += 1
        file_path = mail_folder / filename
        with file_path.open("wb") as fp:
            # Сломано письмом Кошелева от 3 марта 2020
            # во вложениях неопознанный .txt (читается)
            # и неопознанный .eml (!)
            # (ну это результат mimetypes.guess_extension см. выше)
            # на этом .eml get_payload возвращает None и все ломается.
            # В принципе, нам это не нужно, но само явление любопытное
            # FIX: оборачиваем в exception и создаем пустой файл
            try:
                fp.write(part.get_payload(decode=True))
            except TypeError:
                logging.warning(
                    "Сохранение %s не удалось: получен не строковый объект.",
                    filename,
                )
                fp.write(b"\n")


def mark_as_unread(connection: imaplib.IMAP4_SSL, mail_id: str) -> None:
    connection.store(mail_id, "-FLAGS", "(\Seen)")  # noqa:W605


def close_connection(connection: imaplib.IMAP4_SSL) -> None:
    # TODO: добавить retry
    status, response = connection.logout()
    if status != "BYE":
        raise ConnectionError(f"Error logged out email box. Status: {status}")
