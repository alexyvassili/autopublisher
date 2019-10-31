import logging
import os
import shutil

import maildriver
import prepare
import publish
from settings import TMP_FOLDER, TMP_FOLDER_PREFIX
from secrets import MAIL_FROM

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegram.ext import Filters
from telegramlib import owner_only


# Stages
SEARCH, TEXT, PUBLISH, RASPLOAD = range(4)
# Callback data
NEWS, RASP, CANCEL, YES, NO = range(5)

current_mail = maildriver.CurrentMail()  # Хранит состояние текущего письма


@owner_only
def mail_check(update, context):
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("News", callback_data=str(NEWS)),
         InlineKeyboardButton("Rasp", callback_data=str(RASP)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL))
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Проверяю почту...')
    mail_id, mail_folder, mail_metadata = maildriver.load_most_old_mail_from(MAIL_FROM)
    if mail_id is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Новых писем от Кошелева нет!')
        return ConversationHandler.END

    current_mail.init_mail(mail_id, mail_folder, mail_metadata)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Есть письмо')
    context.bot.send_message(chat_id=update.effective_chat.id, text=current_mail.about, reply_markup=reply_markup)
    return SEARCH


def news(update, context):
    """Show new choice of buttons"""
    news_text = current_mail.text
    context.bot.send_message(chat_id=update.effective_chat.id, text=news_text)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Давай текст')
    return TEXT


def news_text(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Текст\n' + update.message.text)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Картинки 1, 2, 3, 4, 5')
    keyboard = [
        [InlineKeyboardButton("Publish", callback_data=str(YES)),
         InlineKeyboardButton("Cancel", callback_data=str(NO))
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Текст письма',
                             reply_markup=reply_markup
                             )
    return PUBLISH


def rasp(update, context):
    """Show new choice of buttons"""
    context.bot.send_message(chat_id=update.effective_chat.id, text='Расписание')
    return ConversationHandler.END


def publish_news(update, context):
    """Show new choice of buttons"""
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем')
    context.bot.send_message(chat_id=update.effective_chat.id, text='Опубликовано')
    return ConversationHandler.END


def cancel(update, context):
    """Show new choice of buttons"""
    current_mail.rollback()
    context.bot.send_message(chat_id=update.effective_chat.id, text='Отмена')
    return ConversationHandler.END


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Fallback echo\n' + update.message.text)


mail_handler = ConversationHandler(
        entry_points=[CommandHandler('mail', mail_check)],
        states={
            SEARCH: [CallbackQueryHandler(news, pattern='^' + str(NEWS) + '$'),
                    CallbackQueryHandler(rasp, pattern='^' + str(RASP) + '$'),
                    CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                    # MessageHandler(Filters.text, news_text),
                    ],
                    # CallbackQueryHandler(two, pattern='^' + str(TWO) + '$'),
                    # CallbackQueryHandler(three, pattern='^' + str(THREE) + '$'),
                    # CallbackQueryHandler(four, pattern='^' + str(FOUR) + '$')],
            TEXT: [MessageHandler(Filters.text, news_text)],
            PUBLISH: [CallbackQueryHandler(publish_news, pattern='^' + str(YES) + '$'),
                      CallbackQueryHandler(cancel, pattern='^' + str(NO) + '$'),
                      ],
            # SECOND: [CallbackQueryHandler(start_over, pattern='^' + str(ONE) + '$'),
            #          CallbackQueryHandler(end, pattern='^' + str(TWO) + '$')]
        },
        fallbacks=[CommandHandler('echo', echo)],
    )
