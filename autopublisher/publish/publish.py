import logging
import os
from time import sleep

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.webdriver import WebDriver, Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from autopublisher.config import FIREFOX_BINARY_PATH, config


log = logging.getLogger(__name__)


display = None


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
        global display
        display = Display(visible=False, size=(1366, 768))
        display.start()
    options = Options()
    options.binary_location = FIREFOX_BINARY_PATH
    driver = webdriver.Firefox(options=options)
    return driver


def close_driver(driver):
    driver.quit()
    if config.server_mode:
        display.stop()


def login_to_site(attempts: int = 3):
    driver: WebDriver = get_driver()
    # TODO: add retry
    while True:
        driver.get(config.site_login_url)
        if "Лотошино" in driver.title:
            break
        attempts -= 1
        if not attempts:
            raise ValueError("Не удалось открыть страницу логина на сайте")
    name_input = driver.find_element(By.ID, 'edit-name')
    name_input.send_keys(config.site_username)
    passwd_input = driver.find_element(By.ID, "edit-pass")
    passwd_input.send_keys(config.site_passwd)
    passwd_input.send_keys(Keys.RETURN)

    wait = WebDriverWait(driver, config.web_driver_wait)
    _ = wait.until(EC.title_contains(config.site_username))
    return driver


def load_jpegs_to_site(driver: WebDriver, folder, jpegs):
    """You must be logged in before uploading!"""
    for filename in jpegs:
        driver.get(config.site_filebrowser_url)
        driver.find_element(By.NAME, "upload").click()
        file_load_input = driver.find_element(By.ID, "edit-imce")
        file_load_input.send_keys(os.path.join(folder, filename))
        driver.find_element(By.ID, "edit-upload").click()
        wait = WebDriverWait(driver, config.web_driver_wait)
        _ = wait.until(EC.presence_of_element_located((By.ID, filename)))
    sleep(1)


def create_rasp_html(jpegs):
    HTML_TEMPLATE = """<p><img src="/sites/default/files/{}" alt="" width="849" height="1200" /></p>"""
    html = ""
    for jpeg in jpegs:
        html += HTML_TEMPLATE.format(jpeg)
    return html


def update_rasp(driver: WebDriver, html):
    driver.get(config.site_rasp_url)
    driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element(By.ID, "edit-body-und-0-value").clear()
    driver.find_element(By.ID, "edit-body-und-0-value").send_keys(html)
    driver.find_element(By.ID, "edit-submit").click()

    wait = WebDriverWait(driver, config.web_driver_wait)
    wait.until(title_not_contains("Редактирование"))
    sleep(1)


def rasp(mail_folder, jpegs):
    driver: WebDriver = login_to_site()
    load_jpegs_to_site(driver, mail_folder, jpegs)
    html = create_rasp_html(jpegs)
    update_rasp(driver, html)
    url = driver.current_url
    close_driver(driver)
    return url


def news(title, html, jpegs):
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    driver.get(config.site_news_url)
    driver.find_element(By.ID, "edit-title").send_keys(title)
    driver.find_element(By.ID, "wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element(By.ID, "edit-body-und-0-value").send_keys(html)

    file_uploader_id = "edit-field-image-und-{}-upload"
    file_uploader_btn = "edit-field-image-und-{}-upload-button"

    for j, filename in enumerate(jpegs):
        driver.find_element(By.ID, file_uploader_id.format(j)).send_keys(filename)
        driver.find_element(By.ID, file_uploader_btn.format(j)).click()
        wait.until(EC.presence_of_element_located((By.ID, file_uploader_id.format(j + 1))))

    driver.find_element(By.ID, "edit-submit").click()

    wait.until(title_not_contains("Создание материала"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    return url


def mainpage(image: "autopublisher.bot.imagebot.Image"):
    driver: WebDriver = login_to_site()
    wait = WebDriverWait(driver, config.web_driver_wait)
    load_jpegs_to_site(driver, image.folder, [image.name])
    driver.get(config.site_mainpage_edit_url)
    text_area = driver.find_element(By.ID, "edit-body-und-0-value")
    text = text_area.text
    jpeg_html = JPEG_TEMPLATE.format(
        start_date=image.start_date,
        end_date=image.end_date,
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
