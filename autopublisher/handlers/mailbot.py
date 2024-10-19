import logging
import traceback
from contextvars import ContextVar

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

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


async def catch_error(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        exc: Exception,
) -> int:
    log.exception(exc)
    tbc = traceback.format_exc()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка!",
    )
    if len(tbc) > TELEGRAM_API_MESSAGE_LIMIT:
        tbc = tbc[-TELEGRAM_API_MESSAGE_LIMIT:]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=tbc)
    mail = current_mail.get()
    if mail:
        mail.rollback()
    return ConversationHandler.END


async def check_mail(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        mail_from: str,
        name_for_msg: str,
) -> int:
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("News", callback_data=str(NEWS)),
         InlineKeyboardButton("Rasp", callback_data=str(RASP)),
         InlineKeyboardButton("Cancel", callback_data=str(CANCEL))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Проверяю почту...",
    )
    mail_id, mail_folder, mail_metadata = maildriver.load_most_old_mail_from(
        mail_from,
    )
    logging.info("Sending request to get mail from %s", mail_from)
    if mail_id is None:
        await context.bot.send_message(
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Есть письмо",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=mail.about,
        reply_markup=reply_markup,
    )
    return SEARCH


@owner_only
async def from_koshelev_check_mail(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
) -> int:
    return await check_mail(update, context, config.mail_from, "Кошелева")


@owner_only
async def from_me_check_mail(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    TODO: Warning! Будет найдено и предложено к обработке
     любое письмо с моего адреса. Хотя я планирую добавить
     что-то типа if "LOTOSHINO" in Subject
    """
    return await check_mail(update, context, config.alternate_mail, "меня")


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mail = get_unwrapped_current_mail()
    if not mail.sentences:
        title, news_sentences = maildriver.get_text_for_news(mail)
        mail.title, mail.sentences = title, news_sentences
    text_to_show = "<" + ">\n<".join(mail.sentences) + ">"
    await context.bot.send_message(
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text_to_show,
        reply_markup=reply_markup,
    )

    return TEXT


async def news_prepare(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=imgs,
        reply_markup=reply_markup,
    )
    return PUBLISH


async def edit_wait(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Кидай текст",
    )
    return TEXT


async def edit_save(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    text = update.message.text
    sentences = [
        line.replace("\n", " ")
        for line in text[1:-1].split(">\n<")
    ]
    mail = get_unwrapped_current_mail()
    mail.sentences = sentences
    return await news(update, context)


async def edit_title_wait(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Новый заголовок новости:",
    )
    return TITLE


async def edit_title_save(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    text = update.message.text
    text = text.strip()
    mail = get_unwrapped_current_mail()
    mail.title = text
    return await news(update, context)


async def rasp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Подготовка...",
    )
    mail = get_unwrapped_current_mail()
    rasp_images = prepare.rasp(mail.folder)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Публикуем расписание",
    )
    try:
        url = publish.rasp(rasp_images)
    except Exception as e:
        return await catch_error(update=update, context=context, exc=e)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Опубликовано!",
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail_clear()
    return ConversationHandler.END


async def publish_news(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    mail = get_unwrapped_current_mail()
    if not mail.title:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ошибка: заголовок новости отсутствует",
        )
        current_mail_clear()
        return ConversationHandler.END

    html = prepare.html_from_sentences(mail.sentences)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Публикуем",
    )
    try:
        url = publish.news(mail.title, html, mail.images)
    except Exception as e:
        return await catch_error(update=update, context=context, exc=e)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Опубликовано!",
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=url)
    current_mail_clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_mail_rollback()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Отмена",
    )
    return ConversationHandler.END


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
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
               MessageHandler(filters.TEXT, edit_save),
               CallbackQueryHandler(cancel, pattern=f"^{CANCEL}$")],
        TITLE: [MessageHandler(filters.TEXT, edit_title_save)],
        PUBLISH: [CallbackQueryHandler(publish_news, pattern=f"^{YES}$"),
                  CallbackQueryHandler(cancel, pattern=f"^{NO}$")],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
