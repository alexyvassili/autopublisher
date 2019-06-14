import os
from load import get_mail_connection, get_mail_message, get_mail_metadata, save_email, close_connection
from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
from secrets import MAIL_FROM


if __name__ == "__main__":
    connection = get_mail_connection()
    status, new_mails_ids = connection.search(None, f'(FROM {MAIL_FROM} UNSEEN)')
    for mail_id in new_mails_ids:
        mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + mail_id.decode())
        message = get_mail_message(connection, mail_id)
        mail_metadata = get_mail_metadata(message)
        save_email(message, mail_folder)
        try:
            html, jpegs = prepare_materials(mail_metadata, mail_folder)

        except:
            pass


        mail_data = save_email(connection, mail_id, mail_folder)
        try:
            if 'расписание' in mail_metadata['Subject'].lower():
                jpegs = prepare_rasp(mail_metadata, mail_folder)
                publish_rasp(mail_folder, jpegs)
            else:
                html, jpegs = prepare_news(mail_metadata, mail_folder)
                publish_news(html, jpegs)
        except Exception as e:
            mark_as_unread(connection, mail_id)
        remove_folder(mail_folder)
        
    close_connection(connection)



    new_mails_ids = get_new_mails()
