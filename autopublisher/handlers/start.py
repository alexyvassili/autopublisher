from telegram.ext import CommandHandler

from autopublisher.utils.telegram import owner_only


@owner_only
def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, хозяин!",
    )


start_handler = CommandHandler("start", start)
