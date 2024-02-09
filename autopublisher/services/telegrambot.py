import logging

from telegram.ext import Updater

from autopublisher.handlers.mailbot import mail_handler
from autopublisher.handlers.imagebot import image_handler
from autopublisher.handlers.start import start_handler
from autopublisher.handlers.echo import echo_handler
from autopublisher.handlers.any_handler import any_handler
from autopublisher.handlers.error import error_handler
from autopublisher.secrets import BOT_TOKEN, BOT_PROXY


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

    def start(self):
        updater = Updater(token=BOT_TOKEN, use_context=True, request_kwargs=BOT_PROXY)
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
