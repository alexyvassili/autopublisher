import logging

from telegram.ext import Updater
from yarl import URL

from autopublisher.handlers.mailbot import mail_handler
from autopublisher.handlers.imagebot import image_handler
from autopublisher.handlers.start import start_handler
from autopublisher.handlers.echo import echo_handler
from autopublisher.handlers.any_handler import any_handler
from autopublisher.handlers.error import error_handler


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


HANDLERS = [
    start_handler,
    mail_handler,
    image_handler,
    echo_handler,
    any_handler
]

ERROR_HANDLERS = [error_handler]


class TelegramBot:

    def __init__(
        self, *,
        token: str,
        proxy_url: URL | None = None,
        proxy_port: int | None = None,
        proxy_username: str | None = None,
        proxy_passwd: str | None = None
    ):
        from autopublisher.config import config
        log.info("SERVER MODE %s", config.server_mode)
        self.token = token
        self.proxy_url = proxy_url
        if self.proxy_url and proxy_port:
            self.proxy_url = self.proxy_url.with_port(proxy_port)
        self.proxy_username = proxy_username
        self.proxy_passwd = proxy_passwd

    @property
    def proxy_kwargs(self):
        proxy_args = dict()
        if self.proxy_url:
            proxy_args["proxy_url"] = self.proxy_url
        if self.proxy_username and self.proxy_passwd:
            proxy_args["urllib3_proxy_kwargs"] = {
                "username": self.proxy_username,
                "password": self.proxy_passwd,
            }
        return proxy_args

    def start(self):
        updater = Updater(
            token=self.token,
            use_context=True,
            request_kwargs=self.proxy_kwargs,
        )
        dispatcher = updater.dispatcher
        for handler in HANDLERS:
            dispatcher.add_handler(handler)

        for error_handler in ERROR_HANDLERS:
            dispatcher.add_error_handler(error_handler)
        updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()
