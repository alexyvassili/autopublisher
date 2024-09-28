import logging
import traceback

from autopublisher.config import TELEGRAM_API_MESSAGE_LIMIT


def error_handler(update, context):
    """Log Errors caused by Updates."""
    logging.warning('Update "%s" caused error "%s"', update, context.error)
    tbc = traceback.format_exc()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка!",
    )
    if len(tbc) > TELEGRAM_API_MESSAGE_LIMIT:
        tbc = tbc[-TELEGRAM_API_MESSAGE_LIMIT:]
    context.bot.send_message(chat_id=update.effective_chat.id, text=tbc)
