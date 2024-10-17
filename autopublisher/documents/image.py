import logging
import random
import shutil
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Self

import pytz
import telegram.update

from autopublisher.config import config
from autopublisher.utils.file import format_img_name


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


def get_salt(size: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))


def iso_fmt_dt_now(tz: pytz.timezone = DEFAULT_TZ) -> str:  # type: ignore[valid-type]
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


def get_start_date(tz: pytz.timezone = DEFAULT_TZ) -> datetime.date:  # type: ignore[valid-type]
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
    start_date: datetime.date  # type: ignore[valid-type]
    end_date: "datetime.date | None" = None  # type: ignore[valid-type]

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
    def start_date_iso(self) -> str | None:
        if self.start_date:
            return self.start_date.isoformat()  # type: ignore[attr-defined]

    @property
    def end_date_iso(self) -> str | None:
        if self.end_date:
            return self.end_date.isoformat()

    @classmethod
    def from_telegram_file(cls, image_file: telegram.files.file.File) -> Self:
        image_folder, image_name = download_image(image_file)
        return Image(  # type: ignore[return-value]
            name=image_name,
            folder=image_folder,
            start_date=get_start_date(),
        )

    def clear(self) -> None:
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()  # type: ignore[misc]
