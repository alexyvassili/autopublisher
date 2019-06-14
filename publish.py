import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


from secrets import *
from settings import *


class title_not_contains(object):
    """ An expectation for checking that the title contains a case-sensitive
    substring. title is the fragment of title expected
    returns True when the title matches, False otherwise
    """
    def __init__(self, title):
        self.title = title

    def __call__(self, driver):
        return self.title not in driver.title


def login_to_site():
	driver = webdriver.Firefox()
	driver.get(SITE_LOGIN_URL)
	assert "Лотошино" in driver.title
	name_input = driver.find_element_by_id('edit-name')
	name_input.send_keys(SITE_USERNAME)
	passwd_input = driver.find_element_by_id("edit-pass")
	passwd_input.send_keys(SITE_PASSWORD)
	passwd_input.send_keys(Keys.RETURN)

	wait = WebDriverWait(driver, 20)
	element = wait.until(EC.title_contains(SITE_USERNAME))


def load_jpegs_to_site(driver, folder, jpegs):
	"""You must be logged in before uploading!"""
	for filename in jpegs:
		driver.get(SITE_FILEBROWSER_URL)
		driver.find_element_by_name("upload").click()
		file_load_input = driver.find_element_by_id("edit-imce")
		file_load_input.send_keys(os.path.join(folder, filename))
		driver.find_element_by_id("edit-upload").click()
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
	driver.find_element_by_id("edit-body-und-0-value").send_keys(HTML)
	driver.find_element_by_id("edit-submit").click()

	wait.until(title_not_contains("Редактирование"))
	sleep(1)


def publish_rasp(mail_folder, jpegs):
	driver = login_to_site()
	load_jpegs_to_site(driver, mail_folder, jpegs)
	html = create_rasp_html(jpegs)
	update_rasp(driver, html)
	driver.close()
