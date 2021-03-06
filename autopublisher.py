import os
import time
import shutil
from datetime import datetime

import mail
import prepare
import publish
from yandex import load_files_from_yandex_disk_folder
from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
from secrets import MAIL_FROM


def telegram_check():
    yield "Проверяю почту..."
    connection = mail.get_connection()
    new_mails_ids = mail.get_new_mails_from(connection, MAIL_FROM)

    for mail_id in new_mails_ids:
        if len(mail_id) == 0:
            continue
        mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + mail_id.decode())
        message = mail.get_message(connection, mail_id)
        mail_metadata = mail.get_mail_metadata(message)
        yield 'Нашел письмо от Кошелева: "{}"'.format(mail_metadata['Subject'])
        mail.save_email(message, mail_folder)

        try:
            if 'расписание' in mail_metadata['Subject'].lower():
                yield "Похоже, это расписание"
                if 30 > int(time.strftime("%d")) > 20:  # если конец месяца - публиковать еще рано
                    yield "Но публиковать его еще рано"
                    raise ValueError('Rasp publish only on start of month')
                yield "Обрабатываем..."
                jpegs = prepare.rasp(mail_folder)
                url = publish.rasp(mail_folder, jpegs)
                yield "Опубликовано, проверь"
                yield url
            else:
                yield "Похоже на новость, пробуем опубликовать"
                prepare.news_folder(mail_folder)
                title, html, jpegs = prepare.news(mail_folder)
                url = publish.news(title, html, jpegs)
                yield "Опубликовано, проверь"
                yield url
        except BaseException as e:
            yield "Не получилось опубликовать информацию"
            mail.mark_as_unread(connection, mail_id)
            mail.close_connection(connection)
            shutil.rmtree(mail_folder)
            raise e
        shutil.rmtree(mail_folder)

    mail.close_connection(connection)


def telegram_yandex_check(yandex_disk_link):
    yield "Скачиваем с Яндекса..."
    mail_folder = "/tmp/yandex_loaded_" + datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
    if os.path.exists(mail_folder):
        shutil.rmtree(mail_folder)
    os.makedirs(mail_folder)

    try:
        load_files_from_yandex_disk_folder(yandex_disk_link, target_folder=mail_folder)
        yield "Подготавливаем..."
        prepare.news_folder(mail_folder)  # заглушка для распознавания разных новостей
        yield "Публикуем..."
        title, html, jpegs = prepare.news(mail_folder)
        url = publish.news(title, html, jpegs)
        yield "Опубликовано, проверь"
        yield url
    except BaseException as e:
        yield "Не получилось опубликовать информацию"
        shutil.rmtree(mail_folder)
        raise e
    shutil.rmtree(mail_folder)


if __name__ == "__main__":
    connection = mail.get_connection()
    new_mails_ids = mail.get_new_mails_from(connection, MAIL_FROM)

    for mail_id in new_mails_ids:
        if len(mail_id) == 0:
            continue
        mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + mail_id.decode())
        message = mail.get_message(connection, mail_id)
        mail_metadata = mail.get_mail_metadata(message)
        mail.save_email(message, mail_folder)

        try:
            if 'расписание' in mail_metadata['Subject'].lower():
                jpegs = prepare.rasp(mail_folder)
                publish.rasp(mail_folder, jpegs)
            else:
                prepare.news_folder(mail_folder)
                title, html, jpegs = prepare.news(mail_folder)
                publish.news(title, html, jpegs)
        except BaseException as e:
            mail.mark_as_unread(connection, mail_id)
            mail.close_connection(connection)
            shutil.rmtree(mail_folder)
            raise e
        shutil.rmtree(mail_folder)
        
    mail.close_connection(connection)
