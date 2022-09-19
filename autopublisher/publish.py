import os
from time import sleep

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


from secrets import *
from settings import *

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
    if SERVER_MODE:
        global display
        display = Display(visible=0, size=(1366, 768))
        display.start()
    driver = webdriver.Firefox()
    return driver


def close_driver(driver):
    driver.quit()
    if SERVER_MODE:
        display.stop()


def login_to_site():
    driver = get_driver()
    driver.get(SITE_LOGIN_URL)
    assert "Лотошино" in driver.title
    name_input = driver.find_element_by_id('edit-name')
    name_input.send_keys(SITE_USERNAME)
    passwd_input = driver.find_element_by_id("edit-pass")
    passwd_input.send_keys(SITE_PASSWORD)
    passwd_input.send_keys(Keys.RETURN)

    wait = WebDriverWait(driver, 20)
    element = wait.until(EC.title_contains(SITE_USERNAME))
    return driver


def load_jpegs_to_site(driver, folder, jpegs):
    """You must be logged in before uploading!"""
    for filename in jpegs:
        driver.get(SITE_FILEBROWSER_URL)
        driver.find_element_by_name("upload").click()
        file_load_input = driver.find_element_by_id("edit-imce")
        file_load_input.send_keys(os.path.join(folder, filename))
        driver.find_element_by_id("edit-upload").click()
        wait = WebDriverWait(driver, 20)
        element = wait.until(EC.presence_of_element_located((By.ID, filename)))
    sleep(1)


def create_rasp_html(jpegs):
    HTML_TEMPLATE = """<p><img src="/sites/default/files/{}" alt="" width="849" height="1200" /></p>"""
    html = ""
    for jpeg in jpegs:
        html += HTML_TEMPLATE.format(jpeg)
    return html


def update_rasp(driver, html):
    driver.get(SITE_RASP_URL)
    driver.find_element_by_id("wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element_by_id("edit-body-und-0-value").clear()
    driver.find_element_by_id("edit-body-und-0-value").send_keys(html)
    driver.find_element_by_id("edit-submit").click()

    wait = WebDriverWait(driver, 20)
    wait.until(title_not_contains("Редактирование"))
    sleep(1)


def rasp(mail_folder, jpegs):
    driver = login_to_site()
    load_jpegs_to_site(driver, mail_folder, jpegs)
    html = create_rasp_html(jpegs)
    update_rasp(driver, html)
    url = driver.current_url
    close_driver(driver)
    return url


def news(title, html, jpegs):
    driver = login_to_site()
    wait = WebDriverWait(driver, 20)
    driver.get(SITE_NEWS_URL)
    driver.find_element_by_id("edit-title").send_keys(title)
    driver.find_element_by_id("wysiwyg-toggle-edit-body-und-0-value").click()
    driver.find_element_by_id("edit-body-und-0-value").send_keys(html)

    file_uploader_id = "edit-field-image-und-{}-upload"
    file_uploader_btn = "edit-field-image-und-{}-upload-button"

    for j, filename in enumerate(jpegs):
        driver.find_element_by_id(file_uploader_id.format(j)).send_keys(filename)
        driver.find_element_by_id(file_uploader_btn.format(j)).click()
        wait.until(EC.presence_of_element_located((By.ID, file_uploader_id.format(j + 1))))

    driver.find_element_by_id("edit-submit").click()

    wait.until(title_not_contains("Создание материала"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    return url


def mainpage(image: 'imagebot.Image'):
    driver = login_to_site()
    wait = WebDriverWait(driver, 20)
    load_jpegs_to_site(driver, image.folder, [image.name])
    driver.get(SITE_MAINPAGE_EDIT)
    text_area = driver.find_element_by_id("edit-body-und-0-value")
    text = text_area.text
    jpeg_html = JPEG_TEMPLATE.format(
        start_date=image.start_date,
        end_date=image.end_date,
        jpeg=f"/sites/default/files/{image.name}",
    )
    html = jpeg_html + text
    text_area.clear()
    text_area.send_keys(html)
    driver.find_element_by_id("edit-submit").click()
    wait.until(title_not_contains("Редактирование"))
    sleep(1)
    url = driver.current_url
    close_driver(driver)
    return url
