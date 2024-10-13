import telegram.update
from telegram.ext import Filters, MessageHandler
from telegram.ext.callbackcontext import CallbackContext


def any_answer(
        update: telegram.update.Update, context: CallbackContext,
) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="А больше я ничего и не умею!",
    )


any_handler = MessageHandler(Filters.all, any_answer)
