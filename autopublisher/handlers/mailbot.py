import logging
import traceback
from contextvars import ContextVar

import telegram.update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)
from telegram.ext.callbackcontext import CallbackContext

from autopublisher.config import TELEGRAM_API_MESSAGE_LIMIT, config
from autopublisher.mail import maildriver
from autopublisher.publish import prepare, publish
from autopublisher.utils.telegram import owner_only


log = logging.getLogger(__name__)


# Stages
SEARCH, TEXT, TITLE, PUBLISH, RASPLOAD = range(5)
# Callback data
NEWS, RASP, CANCEL, YES, NO, EDIT, EDIT_TITLE = range(7)


CurrentMailT = ContextVar[maildriver.CurrentMail | None]
current_mail: CurrentMailT = ContextVar("current_mail", default=None)


def get_unwrapped_current_mail() -> maildriver.CurrentMail:
    mail = current_mail.get()
    if mail is None:
        raise RuntimeError("Current Mail is None")
    return mail


def current_mail_clear() -> None:
    mail = current_mail.get()
    if mail:
        mail.clear()
    current_mail.set(None)


def current_mail_rollback() -> None:
    mail = current_mail.get()
    if mail:
        mail.rollback()
    current_mail.set(None)


def catch_error(
        update: telegram.update.Update,
        context: CallbackContext,
        exc: Exception,
) -> int:
    log.exception(exc)
    tbc = traceback.format_exc()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка!",
    )
    if len(tbc) > TELEGRAM_API_MESSAGE_LIMIT:
        tbc = tbc[-TELEGRAM_API_MESSAGE_LIMIT:]
    context.bot.send_message(chat_id=update.effective_chat.id, text=tbc)
    mail = current_mail.get()
    if mail:
        mail.rollback()
    return ConversationHandler.END


def check_mail(
        update: telegram.update.Update,
        context: CallbackContext,
        mail_from: str,
        name_for_msg: str,
) -> int:
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("News", callback_data=str(NEWS)),
         InlineKeyboardButton("Rasp", callback_data=str(RASP)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL)),
         ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Проверяю почту...",
    )
    mail_id, mail_folder, mail_metadata = maildriver.load_most_old_mail_from(
        mail_from,
    )
    logging.info("Sending request to get mail from %s", mail_from)
    if mail_id is None:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Новых писем от {name_for_msg} нет!",
        )
        return ConversationHandler.END

    if not mail_folder or not mail_metadata:
        log.error(
            "Письмо было загружено, "
            "однако mail_folder или mail_metadata отсутствуют."  # noqa:COM812
        )
        log.error("Mail folder: %r", mail_folder)
        log.error("Mail metadata: %r", mail_metadata)

        raise RuntimeError(
            "Письмо было загружено, "
            "однако mail_folder или mail_metadata отсутствуют."  # noqa:COM812
        )

    mail = maildriver.CurrentMail(
        mail_id=mail_id,
        mail_folder=mail_folder,
        mail_metadata=mail_metadata,
    )
    current_mail.set(mail)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Есть письмо",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mail.about,
        reply_markup=reply_markup,
    )
    return SEARCH


@owner_only
def from_koshelev_check_mail(
        update: telegram.update.Update,
        context: CallbackContext,
) -> int:
    return check_mail(update, context, config.mail_from, "Кошелева")


@owner_only
def from_me_check_mail(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    """
    TODO: Warning! Будет найдено и предложено к обработке
     любое письмо с моего адреса. Хотя я планирую добавить
     что-то типа if "LOTOSHINO" in Subject
    """
    return check_mail(update, context, config.alternate_mail, "меня")


def news(update: telegram.update.Update, context: CallbackContext) -> int:
    mail = get_unwrapped_current_mail()
    if not mail.sentences:
        title, news_sentences = maildriver.get_text_for_news(mail)
        mail.title, mail.sentences = title, news_sentences
    text_to_show = "<" + ">\n<".join(mail.sentences) + ">"
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Title: {mail.title}",
    )
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=str(YES)),
         InlineKeyboardButton("Edit", callback_data=str(EDIT)),
         InlineKeyboardButton("Edit title", callback_data=str(EDIT_TITLE)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text_to_show,
        reply_markup=reply_markup,
    )

    return TEXT


def news_prepare(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    mail = get_unwrapped_current_mail()
    mail.images = maildriver.get_images_for_news(mail)
    if mail.images:
        imgs = "\n".join(
            f"{i+1}) {img}"
            for i, img in enumerate(mail.images)
        )
    else:
        imgs = "Картинок нет."

    keyboard = [
        [InlineKeyboardButton("Publish", callback_data=str(YES)),
         InlineKeyboardButton("Cancel", callback_data=str(NO))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=imgs,
        reply_markup=reply_markup,
    )
    return PUBLISH


def edit_wait(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Кидай текст",
    )
    return TEXT


def edit_save(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    text = update.message.text
    sentences = [
        line.replace("\n", " ")
        for line in text[1:-1].split(">\n<")
    ]
    mail = get_unwrapped_current_mail()
    mail.sentences = sentences
    return news(update, context)


def edit_title_wait(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Новый заголовок новости:",
    )
    return TITLE


def edit_title_save(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    text = update.message.text
    text = text.strip()
    mail = get_unwrapped_current_mail()
    mail.title = text
    return news(update, context)


def rasp(update: telegram.update.Update, context: CallbackContext) -> int:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Подготовка...",
    )
    mail = get_unwrapped_current_mail()
    rasp_images = prepare.rasp(mail.folder)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Публикуем расписание",
    )
    try:
        url = publish.rasp(rasp_images)
    except Exception as e:
        return catch_error(update=update, context=context, exc=e)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Опубликовано!",
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail_clear()
    return ConversationHandler.END


def publish_news(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    mail = get_unwrapped_current_mail()
    if not mail.title:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ошибка: заголовок новости отсутствует",
        )
        current_mail_clear()
        return ConversationHandler.END

    html = prepare.html_from_sentences(mail.sentences)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Публикуем",
    )
    try:
        url = publish.news(mail.title, html, mail.images)
    except Exception as e:
        return catch_error(update=update, context=context, exc=e)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Опубликовано!",
    )
    context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail_clear()
    return ConversationHandler.END


def cancel(update: telegram.update.Update, context: CallbackContext) -> int:
    current_mail_rollback()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Отмена",
    )
    return ConversationHandler.END


def echo(update: telegram.update.Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Fallback echo\n{update.message.text}",
    )


mail_handler = ConversationHandler(
    entry_points=[CommandHandler("mail", from_koshelev_check_mail),
                  CommandHandler("mymail", from_me_check_mail)],
    states={
        SEARCH: [CallbackQueryHandler(news, pattern=f"^{NEWS}$"),
                 CallbackQueryHandler(rasp, pattern=f"^{RASP}$"),
                 CallbackQueryHandler(cancel, pattern=f"^{CANCEL}$")],
        TEXT: [CallbackQueryHandler(news_prepare, pattern=f"^{YES}$"),
               CallbackQueryHandler(edit_wait, pattern=f"^{EDIT}$"),
               CallbackQueryHandler(
                   edit_title_wait, pattern=f"^{EDIT_TITLE}$",
               ),
               MessageHandler(Filters.text, edit_save),
               CallbackQueryHandler(cancel, pattern=f"^{CANCEL}$")],
        TITLE: [MessageHandler(Filters.text, edit_title_save)],
        PUBLISH: [CallbackQueryHandler(publish_news, pattern=f"^{YES}$"),
                  CallbackQueryHandler(cancel, pattern=f"^{NO}$")],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
