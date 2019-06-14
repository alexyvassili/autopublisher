import os

import mail
from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
from secrets import MAIL_FROM


if __name__ == "__main__":
    connection = mail.get_connection()
    status, new_mails_ids = connection.search(None, f'(FROM {MAIL_FROM} UNSEEN)')
    for mail_id in new_mails_ids:
        mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + mail_id.decode())
        message = mail.get_message(connection, mail_id)
        mail_metadata = mail.get_mail_metadata(message)
        mail.save_email(message, mail_folder)

        try:
            if 'расписание' in mail_metadata['Subject'].lower():
                jpegs = prepare_rasp(mail_metadata, mail_folder)
                publish_rasp(mail_folder, jpegs)
            else:
                pass
                # html, jpegs = prepare_news(mail_metadata, mail_folder)
                # publish_news(html, jpegs)
        except Exception as e:
            mark_as_unread(connection, mail_id)
        remove_folder(mail_folder)
        
    close_connection(connection)



    new_mails_ids = get_new_mails()
