import logging
import os
import string
import random
import shutil
from datetime import datetime, date
from pathlib import Path
import pytz

from telegram import ChatAction
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler
from telegram.ext import Filters
from telegram.ext.callbackcontext import CallbackContext
import telegram.update

from autopublisher.config import config
from autopublisher.utils.telegram import owner_only
from autopublisher.handlers.mailbot import TEXT, echo
from autopublisher.utils.file import format_jpeg_name
from autopublisher.utils.dateparse import add_date
from autopublisher.publish.publish import mainpage


log = logging.getLogger(__name__)


try:
    import magic
except ImportError as e:
    message = "\n".join([
        "Error while importing python-magic",
        "Libmagic C library installation is needed",
        "Debian/Ubuntu:",
        ">>> apt-get install libmagic1",
        "\n",
        "OSX:",
        ">>> brew install libmagic",
    ])
    log.exception(message)
    raise ImportError(message) from e


class Image:
    def __init__(self):
        self.name: str | None = None
        self.folder: Path | None = None
        self._start_date: datetime.date = None
        self._end_date: datetime.date = None

    @property
    def path(self) -> Path:
        return self.folder / self.name

    @property
    def start_date(self) -> str:
        if self._start_date:
            return self._start_date.isoformat()

    @property
    def end_date(self) -> str:
        if self._end_date:
            return self._end_date.isoformat()

    def create(self, image_file: telegram.files.file.File) -> None:
        tz = pytz.timezone("Europe/Moscow")
        iso_fmt_time = datetime.now(tz=tz).isoformat()
        self.name = format_jpeg_name(f"mainpage_image_{iso_fmt_time}.jpg")
        tmp_folder_name = config.tmp_folder_prefix + get_salt()
        self.folder = config.tmp_folder / tmp_folder_name
        if self.folder.exists():
            shutil.rmtree(self.folder)
        self.folder.mkdir(parents=True)
        image_file.download(self.path)
        self._start_date = datetime.now(tz=tz).date()

    def clear(self) -> None:
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()


current_image = Image()


def get_salt(size: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))


def edit_save(
        update: telegram.update.Update, context: CallbackContext
) -> int:
    text = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Понятно, {text}",
    )
    try:
        current_image._end_date = add_date(text, current_image._start_date)
        if not current_image._end_date:
            raise ValueError("No one regexp in text was found")
    except Exception as e:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Неизвестная дата или интервал:")
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
        return TEXT
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"START DATE: {current_image.start_date}, "
             f"END DATE: {current_image.end_date}",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Загружаем..."
    )
    mainpage(current_image)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Готово!")
    return ConversationHandler.END


@owner_only
def image_loader(
        update: telegram.update.Update, context: CallbackContext
) -> int:
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_DOCUMENT
    )
    file_id = update.message.document.file_id
    newFile = context.bot.get_file(file_id)
    current_image.clear()
    current_image.create(newFile)
    text = magic.from_file(current_image.path)
    logging.info("Loaded image to: %s", current_image.path)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Загружен файл: {}".format(text)
    )
    if not text.startswith("JPEG"):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Это не JPEG файл. Отмена."
        )
        current_image.clear()
        return ConversationHandler.END
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="До какой даты или на какой срок сохранить картинку?"
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.document, image_loader)],
    states={
        TEXT: [MessageHandler(Filters.text, edit_save)],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
