import telegram.update
from telegram.ext import CommandHandler
from telegram.ext.callbackcontext import CallbackContext

from autopublisher.utils.telegram import owner_only


@owner_only
def start(update: telegram.update.Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, хозяин!",
    )


start_handler = CommandHandler("start", start)
