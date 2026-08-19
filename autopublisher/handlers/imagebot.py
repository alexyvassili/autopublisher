import logging
from contextvars import ContextVar

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from autopublisher.documents.image import Image
from autopublisher.handlers.mailbot import NO, TEXT, YES, catch_error, echo
from autopublisher.publish.publish import mainpage
from autopublisher.utils.dateparse import add_date
from autopublisher.utils.telegram import owner_only, send_message


log = logging.getLogger(__name__)


CurrentImageT = ContextVar[Image | None]
current_image: CurrentImageT = ContextVar("current_image", default=None)

LINK_DECISION, LINK = range(2, 4)


def get_chat_id(update: Update) -> int:
    chat = update.effective_chat
    if chat is None:
        raise RuntimeError("Effective chat is None")
    return chat.id


def get_message_text(update: Update) -> str:
    message = update.message
    if message is None or message.text is None:
        raise RuntimeError("Message text is None")
    return message.text


async def publish_image(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    image = current_image.get()
    if image is None:
        raise RuntimeError("Current Image is None")
    chat_id = get_chat_id(update)
    await send_message(
        context,
        chat_id=chat_id,
        text="Загружаем...",
    )
    try:
        mainpage(image)
    except Exception as e:
        return await catch_error(update=update, context=context, exc=e)
    await send_message(
        context,
        chat_id=chat_id,
        text="Готово!",
    )
    return ConversationHandler.END


async def edit_save(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    image = current_image.get()
    if image is None:
        raise RuntimeError("Current Image is None")
    text = get_message_text(update)
    chat_id = get_chat_id(update)
    await send_message(
        context,
        chat_id=chat_id,
        text=f"Понятно, {text}",
    )
    try:
        image.end_date = add_date(text, image.start_date)
        if not image.end_date:
            raise ValueError("No one regexp in text was found")  # noqa:TRY301
    except Exception as e:
        await send_message(
            context,
            chat_id=chat_id,
            text="Неизвестная дата или интервал:",
        )
        await send_message(
            context,
            chat_id=chat_id,
            text=str(e),
        )
        return TEXT
    await send_message(
        context,
        chat_id=chat_id,
        text=f"START DATE: {image.start_date_iso}, "
             f"END DATE: {image.end_date_iso}",
    )
    keyboard = [
        [InlineKeyboardButton("Да", callback_data=str(YES)),
         InlineKeyboardButton("Нет", callback_data=str(NO))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_message(
        context,
        chat_id=chat_id,
        text="Добавить ссылку к картинке?",
        reply_markup=reply_markup,
    )
    return LINK_DECISION


async def link_wait(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    await send_message(
        context,
        chat_id=get_chat_id(update),
        text="Кидай ссылку",
    )
    return LINK


async def link_save(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    image = current_image.get()
    if image is None:
        raise RuntimeError("Current Image is None")
    link = get_message_text(update).strip()
    image.link = link
    await send_message(
        context,
        chat_id=get_chat_id(update),
        text=f"Понятно, {link}",
    )
    return await publish_image(update, context)


@owner_only
async def image_loader(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    current_image.set(None)
    message = update.message
    if message is None:
        raise RuntimeError("Message is None")
    if message.document is None:
        raise RuntimeError("Message document is None")
    user = message.from_user
    username = user.first_name if user is not None else "unknown"
    logging.info("User %s started the conversation.", username)
    chat_id = get_chat_id(update)
    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.UPLOAD_DOCUMENT,
    )
    file_id = message.document.file_id
    image_file = await context.bot.get_file(file_id)
    image = await Image.from_telegram_file(image_file)
    await send_message(
        context,
        chat_id=chat_id,
        text=f"Загружен файл: {image.magic_text}",
    )
    allowed_image_types = {"JPEG", "PNG"}
    if image.type not in allowed_image_types:
        allowed_types_str = ", ".join(allowed_image_types)
        await send_message(
            context,
            chat_id=chat_id,
            text=f"Неподдерживаемый тип изображения. "
                 f"Поддерживаемые типы: {allowed_types_str}. Отмена.",
        )
        return ConversationHandler.END

    current_image.set(image)
    await send_message(
        context,
        chat_id=chat_id,
        text="До какой даты или на какой срок сохранить картинку?",
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Document.ALL, image_loader)],
    states={
        TEXT: [MessageHandler(filters.TEXT, edit_save)],
        LINK_DECISION: [
            CallbackQueryHandler(link_wait, pattern=f"^{YES}$"),
            CallbackQueryHandler(publish_image, pattern=f"^{NO}$"),
        ],
        LINK: [MessageHandler(filters.TEXT, link_save)],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
