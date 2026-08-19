import asyncio
import logging
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from telegram import Message, Update
from telegram.error import TimedOut
from telegram.ext import ContextTypes

from autopublisher.config import (
    TELEGRAM_SEND_MESSAGE_RETRY_ATTEMPTS,
    TELEGRAM_SEND_MESSAGE_RETRY_DELAY_SECONDS,
    config,
)


log = logging.getLogger(__name__)


BotHandlerT = Callable[..., Coroutine]  # type: ignore[type-arg]


async def send_message(
        context: ContextTypes.DEFAULT_TYPE,
        **kwargs: Any,
) -> Message:
    for attempt in range(TELEGRAM_SEND_MESSAGE_RETRY_ATTEMPTS):
        try:
            return await context.bot.send_message(**kwargs)
        except TimedOut:
            if attempt == TELEGRAM_SEND_MESSAGE_RETRY_ATTEMPTS - 1:
                raise

            retry_delay = (
                TELEGRAM_SEND_MESSAGE_RETRY_DELAY_SECONDS * (attempt + 1)
            )
            log.debug(
                "Telegram send_message timed out on attempt %s/%s",
                attempt + 1,
                TELEGRAM_SEND_MESSAGE_RETRY_ATTEMPTS,
            )
            log.warning(
                "Telegram send_message timed out, retrying in %s seconds",
                retry_delay,
            )
            await asyncio.sleep(retry_delay)

    raise RuntimeError("Unreachable retry loop exit")


def owner_only(bot_handler: BotHandlerT) -> BotHandlerT:

    @wraps(bot_handler)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        owner_id = config.telegram_bot_owner_id
        if update.message.from_user.id != owner_id:
            await send_message(
                context,
                chat_id=update.effective_chat.id,
                text="Ты не мой хозяин",
            )
            return
        return await bot_handler(update, context)

    return wrapper
