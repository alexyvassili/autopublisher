import logging

import maildriver
import prepare
import publish
from secrets import MAIL_FROM

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegramlib import owner_only


# Stages
SEARCH, TEXT, PUBLISH, RASPLOAD = range(4)
# Callback data
NEWS, RASP, CANCEL, YES, NO, EDIT = range(6)

current_mail = maildriver.CurrentMail()  # Хранит состояние текущего письма


@owner_only
def mail_check(update, context):
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
    title, news_sentences = maildriver.get_text_for_news(current_mail)
    current_mail.title, current_mail.sentences = title, news_sentences
    text_to_show = '<' + '>\n<'.join(news_sentences) + '>'
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Title: {title}")
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=str(YES)),
         # InlineKeyboardButton("Edit", callback_data=str(EDIT)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL)),
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_to_show, reply_markup=reply_markup)

    return TEXT


def news_prepare(update, context):
    current_mail.images = maildriver.get_images_for_news(current_mail)
    if current_mail.images:
        imgs = "\n".join(f"{i+1}) {img}" for i, img in enumerate(current_mail.images))
    else:
        imgs = "Картинок нет."

    keyboard = [
        [InlineKeyboardButton("Publish", callback_data=str(YES)),
         # InlineKeyboardButton("Edit", callback_data=str(EDIT)),
         InlineKeyboardButton("Cancel", callback_data=str(NO)),
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=imgs,
                             reply_markup=reply_markup
                             )
    return PUBLISH


def rasp(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Подготовка...')
    jpegs = prepare.rasp(current_mail.folder)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем расписание')
    url = publish.rasp(current_mail.folder, jpegs)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Опубликовано!')
    context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail.clear()
    return ConversationHandler.END


def publish_news(update, context):
    html = prepare.html_from_sentences(current_mail.sentences)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем')
    url = publish.news(current_mail.title, html, current_mail.images)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Опубликовано!')
    context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail.clear()
    return ConversationHandler.END


def cancel(update, context):
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
                     ],
            TEXT: [CallbackQueryHandler(news_prepare, pattern='^' + str(YES) + '$'),
                   CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                   ],
            PUBLISH: [CallbackQueryHandler(publish_news, pattern='^' + str(YES) + '$'),
                      CallbackQueryHandler(cancel, pattern='^' + str(NO) + '$'),
                      ],
        },
        fallbacks=[CommandHandler('echo', echo)],
    )
