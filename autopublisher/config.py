import platform

from dataclasses import dataclass
from yarl import URL


# ##### PLATFORM-DEFINED CONSTANTS ##### #
if platform.system().lower() == "darwin":
    FIREFOX_BINARY_PATH = "/Applications/Firefox.app/Contents/MacOS/firefox"
    SOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    IMAGEMAGICK_PATH = "/opt/homebrew/bin/convert"
else:
    FIREFOX_BINARY_PATH = "/usr/bin/firefox"
    SOFFICE_PATH = "/usr/bin/soffice"
    IMAGEMAGICK_PATH = "/usr/local/bin/convert"


# ##### TELEGRAM SETTINGS ##### #
TELEGRAM_API_MESSAGE_LIMIT = 4096

# ##### BOT SETTINGS ##### #
TMP_FOLDER = "/tmp"
TMP_FOLDER_PREFIX = "autopublisher_"

# ##### SITE SETTINGS ##### #
SITE_LOGIN_PATH = "user"
SITE_FILEBROWSER_PATH = "imce"
SITE_RASP_PATH = "node/18/edit"
SITE_NEWS_PATH = "node/add/news"
SITE_MAINPAGE_EDIT_PATH = "node/17/edit"


@dataclass
class Config:
    server_mode: str | None = None

    telegram_bot_owner_id: int | None = None

    mail_server: str | None = None
    mail_login: str | None = None
    mail_passwd: str | None = None
    mail_from: str | None = None
    alternate_mail: str | None = None
    site_url: URL | None = None
    site_username: str | None = None
    site_passwd: str | None = None

    rasp_image_format: str = "png"

    web_driver_wait: int = 20

    @property
    def tmp_folder(self) -> str:
        return TMP_FOLDER

    @property
    def tmp_folder_prefix(self) -> str:
        return TMP_FOLDER_PREFIX

    # Selenium driver require string URLs
    @property
    def site_login_url(self) -> str:
        return str(self.site_url / SITE_LOGIN_PATH)

    @property
    def site_rasp_url(self) -> str:
        return str(self.site_url / SITE_RASP_PATH)

    @property
    def site_filebrowser_url(self) -> str:
        return str(self.site_url / SITE_FILEBROWSER_PATH)

    @property
    def site_news_url(self) -> str:
        return str(self.site_url / SITE_NEWS_PATH)

    @property
    def site_mainpage_edit_url(self) -> str:
        return str(self.site_url / SITE_MAINPAGE_EDIT_PATH)


config = Config()
