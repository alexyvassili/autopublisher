import telegram.update
from telegram.ext import Filters, MessageHandler
from telegram.ext.callbackcontext import CallbackContext


def echo(
        update: telegram.update.Update, context: CallbackContext,
) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=update.message.text,
    )


echo_handler = MessageHandler(Filters.text, echo)
