import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from autopublisher.config import TELEGRAM_API_MESSAGE_LIMIT


log = logging.getLogger(__name__)


async def error_handler(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log Errors caused by Updates."""
    logging.warning('Update "%s" caused error "%s"', update, context.error)
    tbc = traceback.format_exc()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка!",
    )
    if len(tbc) > TELEGRAM_API_MESSAGE_LIMIT:
        tbc = tbc[-TELEGRAM_API_MESSAGE_LIMIT:]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=tbc)
