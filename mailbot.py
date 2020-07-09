import logging
from datetime import datetime

import maildriver
import prepare
import publish
from secrets import MAIL_FROM, ALTERNATE_MAIL
from settings import MONTHS

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegram.ext import Filters
from telegramlib import owner_only


# Stages
SEARCH, TEXT, IMG_EXPIRE, PUBLISH, PUBLISH_MAINPAGE_IMG, RASPLOAD = range(6)
# Callback data
NEWS, RASP, IMG, CANCEL, YES, NO, EDIT = range(7)

current_mail = maildriver.CurrentMail()  # Хранит состояние текущего письма


def check_mail(update, context, mail_from, name_for_msg):
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("News", callback_data=str(NEWS)),
         InlineKeyboardButton("Rasp", callback_data=str(RASP)),
         InlineKeyboardButton("Img", callback_data=str(IMG)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL))
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Проверяю почту...')
    mail_id, mail_folder, mail_metadata = maildriver.load_most_old_mail_from(mail_from)
    if mail_id is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Новых писем от {name_for_msg} нет!')
        return ConversationHandler.END

    current_mail.init_mail(mail_id, mail_folder, mail_metadata)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Есть письмо')
    context.bot.send_message(chat_id=update.effective_chat.id, text=current_mail.about, reply_markup=reply_markup)
    return SEARCH


@owner_only
def from_koshelev_check_mail(update, context):
    return check_mail(update, context, MAIL_FROM, 'Кошелева')


@owner_only
def from_me_check_mail(update, context):
    """
    Warning! Будет найдено и предложено к обработке любое письмо с моего адреса
    Хотя я планирую добавить что-то типа if "LOTOHA" in Subject
    """
    return check_mail(update, context, ALTERNATE_MAIL, 'меня')


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


def image_expire(update, context):
    text = update.message.text
    try:
        day, month = text.split(' ')
        day = int(day)
    except ValueError:
        return "BAD NUM"
    if month not in MONTHS:
        return "BAD MONTH"
    year = datetime.today().year
    dt = datetime(year, month, day)
    if dt < datetime.today():
        dt = datetime(year, month, day)
    current_mail.image_expired = dt.isoformat()
    msg = f"Картинка: {current_mail.mainpage_img}\nДо: {current_mail.image_expired}"
    keyboard = [
        [InlineKeyboardButton("Publish", callback_data=str(YES)),
         InlineKeyboardButton("Cancel", callback_data=str(NO)),
         ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=msg,
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


def img(update, context):
    current_mail.images = maildriver.get_images_for_news(current_mail)
    if current_mail.images:
        if len(current_mail.images) > 1:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Слишком много картинок",
                                     )
            return ConversationHandler.END
        current_mail.mainpage_img = current_mail.images[0]
        imgs = "\n".join(f"{i+1}) {img}" for i, img in enumerate(current_mail.images))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Картинок не нашел :(",
                                 )
        return ConversationHandler.END
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=imgs)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="До какого числа показывать картинку?")
    return IMG_EXPIRE


def publish_news(update, context):
    html = prepare.html_from_sentences(current_mail.sentences)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем')
    url = publish.news(current_mail.title, html, current_mail.images)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Опубликовано!')
    context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail.clear()
    return ConversationHandler.END


def publish_mainpage_img(update, context):
    # html = prepare.html_from_sentences(current_mail.sentences)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Публикуем')
    # url = publish.news(current_mail.title, html, current_mail.images)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Опубликовано!')
    # context.bot.send_message(chat_id=update.effective_chat.id, text=url)
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
                     CallbackQueryHandler(img, pattern='^' + str(IMG) + '$'),
                     CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                     ],
            TEXT: [CallbackQueryHandler(news_prepare, pattern='^' + str(YES) + '$'),
                   CallbackQueryHandler(edit_wait, pattern='^' + str(EDIT) + '$'),
                   MessageHandler(Filters.text, edit_save),
                   CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
                   ],
            IMG_EXPIRE: [MessageHandler(Filters.text, image_expire)],
            PUBLISH: [CallbackQueryHandler(publish_news, pattern='^' + str(YES) + '$'),
                      CallbackQueryHandler(cancel, pattern='^' + str(NO) + '$'),
                      ],
            PUBLISH_MAINPAGE_IMG: [CallbackQueryHandler(publish_mainpage_img, pattern='^' + str(YES) + '$'),
                      CallbackQueryHandler(cancel, pattern='^' + str(NO) + '$'),
                      ],
        },
        fallbacks=[CommandHandler('echo', echo)],
    )
