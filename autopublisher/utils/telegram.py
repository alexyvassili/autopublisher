from collections.abc import Callable
from functools import wraps
from typing import Any

import telegram.update
from telegram.ext.callbackcontext import CallbackContext

from autopublisher.config import config


def owner_only(bot_handler: Callable) -> Callable:  # type: ignore[type-arg]

    @wraps(bot_handler)
    def wrapper(
            update: telegram.update.Update, context: CallbackContext,
    ) -> Any:
        owner_id = config.telegram_bot_owner_id
        if update.message.from_user.id != owner_id:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ты не мой хозяин",
            )
            return
        return bot_handler(update, context)

    return wrapper
