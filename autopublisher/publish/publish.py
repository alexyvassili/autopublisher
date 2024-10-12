import logging
from contextvars import ContextVar
from time import sleep
from pathlib import Path

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.webdriver import WebDriver, Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from autopublisher.config import FIREFOX_BINARY_PATH, config
from autopublisher.documents.document import HtmlT
from autopublisher.documents.image import Image


log = logging.getLogger(__name__)


display: ContextVar[Display | None] = ContextVar("display", default=None)


JPEG_TEMPLATE = """<!-- MAINPAGE JPEG -->
<!-- START DATE: {start_date}, END DATE: {end_date} -->
<h2><center><img src="{jpeg}" alt="" width="600" /></center></h2>
<!-- END OF MAINPAGE JPEG -->

"""


class title_not_contains(object):
    """ An expectation for checking that the title contains a case-sensitive
    substring. title is the fragment of title expected
    returns True when the title matches, False otherwise
    """
    def __init__(self, title):
        self.title = title

    def __call__(self, driver):
        return self.title not in driver.title


def get_driver():
    if config.server_mode:
        _display = Display(visible=False, size=(1366, 768))
        _display.start()
        display.set(_display)
    options = Options()
    options.binary_location = FIREFOX_BINARY_PATH
    driver = webdriver.Firefox(options=options)
    return driver


def close_driver(driver: WebDriver):
    driver.quit()
    _display = display.get()
    if _display is not None:
        _display.stop()
        display.set(None)


def login_to_site(attempts: int = 3) -> WebDriver:
    driver: WebDriver = get_driver()
    # TODO: add retry
    while True:
        driver.get(str(config.site_login_url))
        if "Лотошино" in driver.title:
            break
        attempts -= 1
        if not attempts:
            raise ValueError("Не удалось открыть страницу логина на сайте")
    name_input = driver.find_element(By.ID, "edit-name")
    name_input.send_keys(config.site_username)
    passwd_input = driver.find_element(By.ID, "edit-pass")
    passwd_input.send_keys(config.site_passwd)
    passwd_input.send_keys(Keys.RETURN)

    wait = WebDriverWait(driver, config.web_driver_wait)
    _ = wait.until(EC.title_contains(config.site_username))
    return driver


def load_jpegs_to_site(*, driver: WebDriver, jpegs: list[Path]):
    """You must be logged in before uploading!"""
    for file_path in jpegs:
        filename = file_path.name
        driver.get(config.site_filebrowser_url)
        driver.find_element(By.NAME, "upload").click()
        file_load_input = driver.find_element(By.ID, "edit-imce")
        file_load_input.send_keys(str(file_path))
        driver.find_element(By.ID, "edit-upload").click()
        wait = WebDriverWait(driver, config.web_driver_wait)
        _ = wait.until(EC.presence_of_element_located((By.ID, filename)))
    sleep(1)


def create_rasp_html(jpegs: list[Path]) -> HtmlT:
    HTML_TEMPLATE = """<p><img src="/sites/default/files/{}" alt="" width="849" height="1200" /></p>"""
    html = ""
    for jpeg in jpegs:
        html += HTML_TEMPLATE.format(jpeg.name)
    return html


def update_rasp(driver: WebDriver, html: HtmlT) -> None:
    driver.get(config.site_rasp_url)
    # driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element(By.ID, "edit-body-und-0-value").clear()
    driver.find_element(By.ID, "edit-body-und-0-value").send_keys(html)
    driver.find_element(By.ID, "edit-submit").click()

    wait = WebDriverWait(driver, config.web_driver_wait)
    wait.until(title_not_contains("Редактирование"))
    sleep(1)


def rasp(jpegs: list[Path]) -> str:
    driver: WebDriver = login_to_site()
    load_jpegs_to_site(driver=driver, jpegs=jpegs)
    html = create_rasp_html(jpegs)
    update_rasp(driver, html)
    url = driver.current_url
    # TODO: менеджер контекста для driver
    close_driver(driver)
    return url


def news(title: str, html: HtmlT, jpegs: list[Path]) -> str:
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    driver.get(config.site_news_url)
    driver.find_element(By.ID, "edit-title").send_keys(title)
    driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element(By.ID, "edit-body-und-0-value").send_keys(html)

    file_uploader_id = "edit-field-image-und-{}-upload"
    file_uploader_btn = "edit-field-image-und-{}-upload-button"

    for j, filename in enumerate(jpegs):
        driver.find_element(
            By.ID, file_uploader_id.format(j)
        ).send_keys(str(filename))
        driver.find_element(
            By.ID, file_uploader_btn.format(j)
        ).click()
        wait.until(EC.presence_of_element_located(
            (By.ID, file_uploader_id.format(j + 1))
        ))

    driver.find_element(By.ID, "edit-submit").click()

    wait.until(title_not_contains("Создание материала"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    return url


def mainpage(image: Image) -> str:
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    load_jpegs_to_site(driver=driver, jpegs=[image.path])
    driver.get(config.site_mainpage_edit_url)
    text_area = driver.find_element(By.ID, "edit-body-und-0-value")
    text = text_area.text
    jpeg_html = JPEG_TEMPLATE.format(
        start_date=image.start_date_iso,
        end_date=image.end_date_iso,
        jpeg=f"/sites/default/files/{image.name}",
    )
    html = jpeg_html + text
    text_area.clear()
    text_area.send_keys(html)
    driver.find_element(By.ID, "edit-submit").click()
    wait.until(title_not_contains("Редактирование"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    return url
