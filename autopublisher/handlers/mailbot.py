import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegram.ext import Filters

from autopublisher.config import config
import autopublisher.mail.maildriver as maildriver
import autopublisher.publish.prepare as prepare
import autopublisher.publish.publish as publish
from autopublisher.utils.telegram import owner_only


# Stages
SEARCH, TEXT, PUBLISH, RASPLOAD = range(4)
# Callback data
NEWS, RASP, CANCEL, YES, NO, EDIT = range(6)

current_mail = maildriver.CurrentMail()  # Хранит состояние текущего письма


def check_mail(update, context, mail_from, name_for_msg):
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
    mail_id, mail_folder, mail_metadata = maildriver.load_most_old_mail_from(mail_from)
    logging.info("Sending request to get mail from %s", mail_from)
    if mail_id is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Новых писем от {name_for_msg} нет!')
        return ConversationHandler.END

    current_mail.init_mail(mail_id, mail_folder, mail_metadata)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Есть письмо')
    context.bot.send_message(chat_id=update.effective_chat.id, text=current_mail.about, reply_markup=reply_markup)
    return SEARCH


@owner_only
def from_koshelev_check_mail(update, context):
    return check_mail(update, context, config.mail_from, 'Кошелева')


@owner_only
def from_me_check_mail(update, context):
    """
    TODO: Warning! Будет найдено и предложено к обработке любое письмо с моего адреса
     Хотя я планирую добавить что-то типа if "LOTOSHINO" in Subject
    """
    return check_mail(update, context, config.alternate_mail, 'меня')


def news(update, context):
    if not current_mail.sentences:
        title, news_sentences = maildriver.get_text_for_news(current_mail)
        current_mail.title, current_mail.sentences = title, news_sentences
    text_to_show = '<' + '>\n<'.join(current_mail.sentences) + '>'
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Title: {current_mail.title}")
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=str(YES)),
         InlineKeyboardButton("Edit", callback_data=str(EDIT)),
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


def edit_wait(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Кидай текст")
    return TEXT


def edit_save(update, context):
    text = update.message.text
    sentences = [line.replace('\n', ' ') for line in text[1:-1].split('>\n<')]
    current_mail.sentences = sentences
    return news(update, context)


def rasp(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Подготовка...')
    rasp_images = prepare.rasp(current_mail.folder)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем расписание')
    url = publish.rasp(current_mail.folder, rasp_images)
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
        entry_points=[CommandHandler('mail', from_koshelev_check_mail),
                      CommandHandler('mymail', from_me_check_mail)],
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
