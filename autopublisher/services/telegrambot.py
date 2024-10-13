import logging
from dataclasses import dataclass
from typing import Any

from telegram.ext import Updater
from yarl import URL

from autopublisher.handlers.any_handler import any_handler
from autopublisher.handlers.echo import echo_handler
from autopublisher.handlers.error import error_handler
from autopublisher.handlers.imagebot import image_handler
from autopublisher.handlers.mailbot import mail_handler
from autopublisher.handlers.start import start_handler


log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)


HANDLERS = [
    start_handler,
    mail_handler,
    image_handler,
    echo_handler,
    any_handler,
]

ERROR_HANDLERS = [error_handler]


@dataclass(frozen=True)
class Proxy:
    url: URL | None
    port: int | None
    username: str | None
    passwd: str | None

    @property
    def full_url(self) -> URL | None:
        if self.url and self.port:
            return self.url.with_port(self.port)
        return self.url

    def to_kwargs(self) -> dict[str, Any]:
        proxy_args = dict()  # noqa:C408
        if self.full_url:
            proxy_args["proxy_url"] = self.full_url
        if self.username and self.passwd:
            proxy_args["urllib3_proxy_kwargs"] = {
                "username": self.username,
                "password": self.passwd,
            }
        return proxy_args


class TelegramBot:

    def __init__(
        self, *,
        token: str,
        proxy: Proxy,
    ):
        from autopublisher.config import config
        log.info("SERVER MODE %s", config.server_mode)
        self.token = token
        self.proxy = proxy

    def start(self) -> None:
        updater = Updater(
            token=self.token,
            use_context=True,
            request_kwargs=self.proxy.to_kwargs(),
        )
        dispatcher = updater.dispatcher
        for handler in HANDLERS:
            dispatcher.add_handler(handler)

        for err_handler in ERROR_HANDLERS:
            dispatcher.add_error_handler(err_handler)
        updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
