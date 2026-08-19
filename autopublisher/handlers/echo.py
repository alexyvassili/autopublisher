from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from autopublisher.utils.telegram import send_message


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_message(
        context,
        chat_id=update.effective_chat.id,
        text=update.message.text,
    )


echo_handler = MessageHandler(filters.TEXT, echo)
