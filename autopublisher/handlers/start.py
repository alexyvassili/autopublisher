from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from autopublisher.utils.telegram import owner_only


@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, хозяин!",
    )


start_handler = CommandHandler("start", start)
