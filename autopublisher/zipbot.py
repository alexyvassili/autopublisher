import logging
import os
import string
import random
import shutil

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegram.ext import Filters
from telegramlib import owner_only

from mailbot import SEARCH, TEXT, PUBLISH, NEWS, RASP, CANCEL, EDIT, YES, NO
from mailbot import news, rasp, cancel, news_prepare, edit_wait, edit_save, publish_news, echo, current_mail

from settings import TMP_FOLDER, TMP_FOLDER_PREFIX


def get_salt(size=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


@owner_only
def arc_loader(update, context):
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("News", callback_data=str(NEWS)),
         InlineKeyboardButton("Rasp", callback_data=str(RASP)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL))
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    file_id = update.message.document.file_id
    newFile = context.bot.get_file(file_id)
    arc_name = 'archive.zip'
    mail_folder = os.path.join(TMP_FOLDER, TMP_FOLDER_PREFIX + get_salt())
    mail_id = None
    mail_metadata = {
        "Date": "Right now",
        "From": "Me",
        "Subject": " ",
        "Body": " ",
        "Attachments": [arc_name]
    }
    if os.path.exists(mail_folder):
        shutil.rmtree(mail_folder)
    os.makedirs(mail_folder)
    newFile.download(os.path.join(mail_folder, arc_name))
    current_mail.init_mail(mail_id, mail_folder, mail_metadata)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Загружено "письмо"')
    context.bot.send_message(chat_id=update.effective_chat.id, text=current_mail.about, reply_markup=reply_markup)
    return SEARCH


arc_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, arc_loader)],
        states={
            SEARCH: [CallbackQueryHandler(news, pattern='^' + str(NEWS) + '$'),
                     CallbackQueryHandler(rasp, pattern='^' + str(RASP) + '$'),
                     CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                     ],
            TEXT: [CallbackQueryHandler(news_prepare, pattern='^' + str(YES) + '$'),
                   CallbackQueryHandler(edit_wait, pattern='^' + str(EDIT) + '$'),
                   MessageHandler(Filters.text, edit_save),
                   CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                   ],
            PUBLISH: [CallbackQueryHandler(publish_news, pattern='^' + str(YES) + '$'),
                      CallbackQueryHandler(cancel, pattern='^' + str(NO) + '$'),
                      ],
        },
        fallbacks=[CommandHandler('echo', echo)],
    )
