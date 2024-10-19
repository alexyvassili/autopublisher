from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters


async def any_answer(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="А больше я ничего и не умею!",
    )


any_handler = MessageHandler(filters.ALL, any_answer)
