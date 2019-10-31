from functools import wraps
from secrets import BOT_OWNER_ID


def owner_only(bot_handler):
    owner_id = BOT_OWNER_ID
    @wraps(bot_handler)
    def wrapper(update, context):
        if update.message.from_user.id != owner_id:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Ты не мой хозяин")
            return
        return bot_handler(update, context)

    return wrapper
