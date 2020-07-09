from secrets import SITE_DOMAIN

SERVER_MODE = True

TMP_FOLDER = "/tmp"
TMP_FOLDER_PREFIX = "autopublisher_"
MAINPAGE_IMAGES_JSON = "mainpage_images.json"

SITE_LOGIN_URL = f"http://{SITE_DOMAIN}/user"
SITE_FILEBROWSER_URL = f"http://{SITE_DOMAIN}/imce"
SITE_RASP_URL = f"http://{SITE_DOMAIN}/node/18/edit"
SITE_NEWS_URL = f"http://{SITE_DOMAIN}/node/add/news"

MONTHS_LIST = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

MONTHS = {i+1: month for i, month in enumerate(MONTHS_LIST)}
