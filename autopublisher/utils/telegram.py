from collections.abc import Callable, Coroutine
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from autopublisher.config import config


BotHandlerT = Callable[..., Coroutine]  # type: ignore[type-arg]


def owner_only(bot_handler: BotHandlerT) -> BotHandlerT:

    @wraps(bot_handler)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        owner_id = config.telegram_bot_owner_id
        if update.message.from_user.id != owner_id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ты не мой хозяин",
            )
            return
        return await bot_handler(update, context)

    return wrapper
