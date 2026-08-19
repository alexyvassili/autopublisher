import logging
from contextvars import ContextVar
from pathlib import Path
from time import sleep

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.webdriver import Options, WebDriver
from selenium.webdriver.support import expected_conditions as EC  # noqa:N812
from selenium.webdriver.support.ui import WebDriverWait

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

RASP_HTML_TEMPLATE = """<p><img src="/sites/default/files/{}" alt="" width="849" height="1200" /></p>"""  # noqa:E501


class title_not_contains:  # noqa:N801
    """ An expectation for checking that the title contains a case-sensitive
    substring. title is the fragment of title expected
    returns True when the title matches, False otherwise
    """
    def __init__(self, title: str):
        self.title = title

    def __call__(self, driver: WebDriver) -> bool:
        return self.title not in driver.title


def get_driver(*, retries: int = 3, wait: int = 3) -> WebDriver:
    if config.server_mode:
        _display = Display(visible=False, size=(1366, 768))
        _display.start()
        display.set(_display)
    options = Options()
    options.binary_location = FIREFOX_BINARY_PATH
    options.page_load_strategy = "none"

    for _ in range(retries):
        try:
            driver = webdriver.Firefox(options=options)
        except Exception:
            log.exception("Unable to create webdriver.Firefox")
            sleep(wait)
        else:
            return driver

    raise RuntimeError("Unable to create webdriver.Firefox")


def close_driver(driver: WebDriver) -> None:
    driver.quit()
    _display = display.get()
    if _display is not None:
        _display.stop()
        display.set(None)


def login_to_site(attempts: int = 3) -> WebDriver:
    if not config.site_username or not config.site_passwd:
        raise RuntimeError("No site username or password provided")
    driver: WebDriver = get_driver()
    # TODO: add retry
    error_message = "Не удалось открыть страницу логина на сайте"
    while True:
        try:
            log.info("Open login page")
            driver.get(str(config.site_login_url))
            sleep(3)
            log.info("Page title: %s", driver.title)
        except Exception as e:
            log.exception("Unable to open site login page")
            attempts -= 1
            if not attempts:
                raise ValueError(error_message) from e
            continue
        if "Лотошино" in driver.title:
            break
        attempts -= 1
        if not attempts:
            raise ValueError(error_message)
    wait = WebDriverWait(driver, config.web_driver_wait)
    wait.until(EC.presence_of_element_located((By.ID, "edit-name")))
    name_input = driver.find_element(By.ID, "edit-name")
    name_input.send_keys(config.site_username)
    passwd_input = driver.find_element(By.ID, "edit-pass")
    passwd_input.send_keys(config.site_passwd)
    passwd_input.send_keys(Keys.RETURN)

    _ = wait.until(EC.title_contains(config.site_username))
    return driver


def load_jpegs_to_site(*, driver: WebDriver, jpegs: list[Path]) -> None:
    """You must be logged in before uploading!"""
    wait = WebDriverWait(driver, config.web_driver_wait)
    for file_path in jpegs:
        filename = file_path.name
        driver.get(config.site_login_url)
        sleep(1)
        driver.get(config.site_filebrowser_url)
        wait.until(EC.presence_of_element_located((By.ID, "edit-upload")))
        driver.find_element(By.NAME, "upload").click()
        wait.until(EC.presence_of_element_located((By.ID, "edit-imce")))
        file_load_input = driver.find_element(By.ID, "edit-imce")
        file_load_input.send_keys(str(file_path))
        wait.until(EC.presence_of_element_located((By.ID, "edit-upload")))
        driver.find_element(By.ID, "edit-upload").click()
        # _ = wait.until(EC.presence_of_element_located((By.ID, filename)))
        sleep(1)
    sleep(1)


def create_rasp_html(jpegs: list[Path]) -> HtmlT:
    html_items = [
        RASP_HTML_TEMPLATE.format(jpeg.name)
        for jpeg in jpegs
    ]
    return "".join(html_items)


def update_rasp(driver: WebDriver, html: HtmlT) -> None:
    driver.get(config.site_rasp_url)
    # Раньше эта строчка работала, потом стала
    #  выдавать ошибку драйвера Selenium
    # driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()  # noqa:ERA001,E501
    log.info("Send rasp html:")
    print(html)
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
    print("Load News title:")
    print(title)
    print()
    print("Load News HTML:")
    print(html)
    print()
    print("Jpegs:")
    for jpeg in jpegs:
        print(jpeg)
    print()
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    log.info("Open site news url")
    driver.get(config.site_news_url)
    log.info("Edit title")
    wait.until(EC.presence_of_element_located((By.ID, "edit-title")))
    driver.find_element(By.ID, "edit-title").send_keys(title)
    wait.until(EC.presence_of_element_located((By.ID, "wysiwyg-toggle-edit-body-und-0-value")))
    driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()
    log.info('Send html')
    wait.until(EC.presence_of_element_located((By.ID, "edit-body-und-0-value")))
    driver.find_element(By.ID, "edit-body-und-0-value").send_keys(html)

    file_uploader_id = "edit-field-image-und-{}-upload"
    file_uploader_btn = "edit-field-image-und-{}-upload-button"

    log.info('Uploading images')
    for j, filename in enumerate(jpegs):
        driver.find_element(
            By.ID, file_uploader_id.format(j),
        ).send_keys(str(filename))
        driver.find_element(
            By.ID, file_uploader_btn.format(j),
        ).click()
        wait.until(EC.presence_of_element_located(
            (By.ID, file_uploader_id.format(j + 1)),
        ))

    log.info('Edit submit')
    driver.find_element(By.ID, "edit-submit").click()

    wait.until(title_not_contains("Создание материала"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    log.info('Done. News page: %s', url)
    return url


def mainpage(image: Image) -> str:
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    load_jpegs_to_site(driver=driver, jpegs=[image.path])
    driver.get(config.site_mainpage_edit_url)
    wait.until(EC.presence_of_element_located((By.ID, "edit-submit")))
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
