from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from autopublisher.utils.telegram import send_message


async def any_answer(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await send_message(
        context,
        chat_id=update.effective_chat.id,
        text="А больше я ничего и не умею!",
    )


any_handler = MessageHandler(filters.ALL, any_answer)
