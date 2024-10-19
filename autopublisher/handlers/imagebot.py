import logging
from contextvars import ContextVar

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from autopublisher.documents.image import Image
from autopublisher.handlers.mailbot import TEXT, catch_error, echo
from autopublisher.publish.publish import mainpage
from autopublisher.utils.dateparse import add_date
from autopublisher.utils.telegram import owner_only


log = logging.getLogger(__name__)


CurrentImageT = ContextVar[Image | None]
current_image: CurrentImageT = ContextVar("current_image", default=None)


async def edit_save(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    image = current_image.get()
    if image is None:
        raise RuntimeError("Current Image is None")
    text = update.message.text
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Понятно, {text}",
    )
    try:
        image.end_date = add_date(text, image.start_date)
        if not image.end_date:
            raise ValueError("No one regexp in text was found")  # noqa:TRY301
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Неизвестная дата или интервал:",
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=str(e),
        )
        return TEXT
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"START DATE: {image.start_date_iso}, "
             f"END DATE: {image.end_date_iso}",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Загружаем...",
    )
    try:
        mainpage(image)
    except Exception as e:
        return await catch_error(update=update, context=context, exc=e)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Готово!",
    )
    return ConversationHandler.END


@owner_only
async def image_loader(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    current_image.set(None)
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_DOCUMENT,
    )
    file_id = update.message.document.file_id
    image_file = await context.bot.get_file(file_id)
    image = await Image.from_telegram_file(image_file)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Загружен файл: {image.magic_text}",
    )
    allowed_image_types = {"JPEG", "PNG"}
    if image.type not in allowed_image_types:
        allowed_types_str = ", ".join(allowed_image_types)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Неподдерживаемый тип изображения. "
                 f"Поддерживаемые типы: {allowed_types_str}. Отмена.",
        )
        return ConversationHandler.END

    current_image.set(image)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="До какой даты или на какой срок сохранить картинку?",
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Document.ALL, image_loader)],
    states={
        TEXT: [MessageHandler(filters.TEXT, edit_save)],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
