import logging
from dataclasses import dataclass

from telegram import Update
from telegram.ext import Application
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

# set higher logging level for httpx
# to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


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
        if self.url is None:
            return self.url

        url = self.url
        if self.port:
            url = self.url.with_port(self.port)

        if self.username:
            if not self.passwd:
                raise ValueError(
                    "Not all of 'proxy username, proxy password' was provided",
                )

            url = url.with_user(self.username).with_password(self.passwd)

        return url


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
        # Create the Application and pass it your bot's token.
        application = Application.builder().token(self.token)
        if self.proxy.full_url:
            application = application.proxy(str(self.proxy.full_url))
        application = application.build()

        for handler in HANDLERS:
            application.add_handler(handler)

        for err_handler in ERROR_HANDLERS:
            application.add_error_handler(err_handler)

        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
