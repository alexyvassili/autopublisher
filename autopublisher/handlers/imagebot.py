import logging
import random
import shutil
import string
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

import pytz
import telegram.update
from telegram import ChatAction
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler
from telegram.ext.callbackcontext import CallbackContext

from autopublisher.config import config
from autopublisher.handlers.mailbot import TEXT, catch_error, echo
from autopublisher.publish.publish import mainpage
from autopublisher.utils.dateparse import add_date
from autopublisher.utils.file import format_img_name
from autopublisher.utils.telegram import owner_only


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


DEFAULT_TZ = pytz.timezone("Europe/Moscow")


def iso_fmt_dt_now(tz: pytz.timezone = DEFAULT_TZ) -> str:
    return datetime.now(tz=tz).isoformat()


def get_img_name() -> str:
    iso_fmt_time = iso_fmt_dt_now()
    return format_img_name(f"mainpage_image_{iso_fmt_time}")


def get_img_download_name(img_name: str) -> str:
    img_name = img_name or get_img_name()
    return f"{img_name}.download"


def get_img_full_name(*, img_name: str, img_type: str = "") -> str:
    img_type = img_type.lower() if img_type else ""
    return f"{img_name}.{img_type}"


def get_image_tmp_folder() -> Path:
    tmp_folder_name = config.tmp_folder_prefix + get_salt()
    folder = config.tmp_folder / tmp_folder_name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    return folder


def get_magic_text(image_path: Path) -> str:
    return magic.from_file(image_path)


def get_possible_type_from_magic_text(magic_text: str) -> str:
    return magic_text.split(" ", 1)[0]


def get_start_date(tz: pytz.timezone = DEFAULT_TZ) -> datetime.date:
    return datetime.now(tz=tz).date()


def download_image(image_file: telegram.files.file.File) -> tuple[Path, str]:
    image_tmp_folder = get_image_tmp_folder()
    img_name = get_img_name()
    image_download_path = image_tmp_folder / get_img_download_name(img_name)
    image_file.download(image_download_path)
    log.info("Loaded image to: %s", image_download_path)
    magic_text = get_magic_text(image_download_path)
    log.info("Magic text: %s", magic_text)
    possible_type = get_possible_type_from_magic_text(magic_text)
    log.info("Possible type: %s", possible_type)
    image_full_name = get_img_full_name(
        img_name=img_name, img_type=possible_type,
    )
    image_path = image_tmp_folder / image_full_name
    shutil.move(image_download_path, image_path)
    log.info("Saved to: %s", image_path)
    return image_tmp_folder, image_full_name


@dataclass
class Image:
    name: str
    folder: Path
    start_date: datetime.date
    end_date: datetime.date = None

    @property
    def path(self) -> Path:
        return self.folder / self.name

    @property
    def ext(self) -> str | None:
        return self.path.suffix

    @property
    def magic_text(self) -> str:
        return magic.from_file(self.path)

    @property
    def type(self) -> str:
        return get_possible_type_from_magic_text(self.magic_text)

    @property
    def start_date_iso(self) -> str:
        if self.start_date:
            return self.start_date.isoformat()

    @property
    def end_date_iso(self) -> str:
        if self.end_date:
            return self.end_date.isoformat()

    @classmethod
    def from_telegram_file(cls, image_file: telegram.files.file.File) -> Self:
        image_folder, image_name = download_image(image_file)
        return Image(
            name=image_name,
            folder=image_folder,
            start_date=get_start_date(),
        )

    def clear(self) -> None:
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()


CurrentImageT = ContextVar[Image | None]
current_image: CurrentImageT = ContextVar("current_image", default=None)


def get_salt(size: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))


def edit_save(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    image = current_image.get()
    text = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Понятно, {text}",
    )
    try:
        image.end_date = add_date(text, image.start_date)
        if not image.end_date:
            raise ValueError("No one regexp in text was found")  # noqa:TRY301
    except Exception as e:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Неизвестная дата или интервал:")
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
        return TEXT
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"START DATE: {image.start_date_iso}, "
             f"END DATE: {image.end_date_iso}",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Загружаем...",
    )
    try:
        mainpage(image)
    except Exception:
        return catch_error(update=update, context=context)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Готово!")
    return ConversationHandler.END


@owner_only
def image_loader(
        update: telegram.update.Update, context: CallbackContext,
) -> int:
    current_image.set(None)
    user = update.message.from_user
    logging.info("User %s started the conversation.", user.first_name)
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_DOCUMENT,
    )
    file_id = update.message.document.file_id
    image_file = context.bot.get_file(file_id)
    image = Image.from_telegram_file(image_file)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Загружен файл: {image.magic_text}",
    )
    allowed_image_types = {"JPEG", "PNG"}
    if image.type not in allowed_image_types:
        allowed_types_str = ", ".join(allowed_image_types)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Неподдерживаемый тип изображения. "
                 f"Поддерживаемые типы: {allowed_types_str}. Отмена.",
        )
        return ConversationHandler.END

    current_image.set(image)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="До какой даты или на какой срок сохранить картинку?",
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.document, image_loader)],
    states={
        TEXT: [MessageHandler(Filters.text, edit_save)],
    },
    fallbacks=[CommandHandler("echo", echo)],
)
