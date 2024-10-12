import logging
from contextvars import ContextVar

import telegram.update
from telegram import ChatAction
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler
from telegram.ext.callbackcontext import CallbackContext

from autopublisher.handlers.mailbot import TEXT, catch_error, echo
from autopublisher.documents.image import Image
from autopublisher.publish.publish import mainpage
from autopublisher.utils.dateparse import add_date
from autopublisher.utils.telegram import owner_only


log = logging.getLogger(__name__)


CurrentImageT = ContextVar[Image | None]
current_image: CurrentImageT = ContextVar("current_image", default=None)


def edit_save(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    image = current_image.get()
    text = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Понятно, {text}",
    )
    try:
        image.end_date = add_date(text, image.start_date)
        if not image.end_date:
            raise ValueError("No one regexp in text was found")  # noqa:TRY301
    except Exception as e:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Неизвестная дата или интервал:")
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
        return TEXT
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"START DATE: {image.start_date_iso}, "
             f"END DATE: {image.end_date_iso}",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Загружаем...",
    )
    try:
        mainpage(image)
    except Exception as e:
        return catch_error(update=update, context=context, exc=e)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Готово!")
    return ConversationHandler.END


@owner_only
def image_loader(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    current_image.set(None)
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_DOCUMENT,
    )
    file_id = update.message.document.file_id
    image_file = context.bot.get_file(file_id)
    image = Image.from_telegram_file(image_file)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Загружен файл: {image.magic_text}",
    )
    allowed_image_types = {"JPEG", "PNG"}
    if image.type not in allowed_image_types:
        allowed_types_str = ", ".join(allowed_image_types)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Неподдерживаемый тип изображения. "
                 f"Поддерживаемые типы: {allowed_types_str}. Отмена.",
        )
        return ConversationHandler.END

    current_image.set(image)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="До какой даты или на какой срок сохранить картинку?",
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.document, image_loader)],
    states={
        TEXT: [MessageHandler(Filters.text, edit_save)],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
