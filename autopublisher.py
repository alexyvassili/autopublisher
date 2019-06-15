import os
import shutil

import mail
import prepare
import publish
from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
from secrets import MAIL_FROM


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
                title, html, jpegs = prepare.news(mail_metadata, mail_folder)
                publish.news(title, html, jpegs)
        except BaseException as e:
            mail.mark_as_unread(connection, mail_id)
            mail.close_connection(connection)
            shutil.rmtree(mail_folder)
            raise e
        shutil.rmtree(mail_folder)
        
    mail.close_connection(connection)
