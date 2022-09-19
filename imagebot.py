import logging
import os
import string
import random
import shutil
from datetime import datetime, date

import telegram
from telegram import ChatAction
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler
from telegram.ext import Filters
from telegramlib import owner_only

from mailbot import TEXT, echo
from file_utils import format_jpeg_name
from dateparse import add_date
from publish import mainpage

from settings import TMP_FOLDER, TMP_FOLDER_PREFIX

try:
    import magic
except ImportError:
    print("Error while importing python-magic")
    print("Libmagic C library installation is needed")
    print("Debian/Ubuntu:")
    print(">>> apt-get install libmagic1")
    print()
    print("OSX:")
    print(">>> brew install libmagic")


class Image:
    def __init__(self):
        self.name = ""
        self.folder = ""
        self._start_date = None
        self._end_date = None

    @property
    def path(self):
        return os.path.join(self.folder, self.name)

    @property
    def start_date(self):
        if self._start_date:
            return self._start_date.isoformat()

    @property
    def end_date(self):
        if self._end_date:
            return self._end_date.isoformat()

    def create(self, image_file: telegram.files.file.File):
        iso_fmt_time = datetime.now().isoformat()
        self.name = format_jpeg_name(f'mainpage_image_{iso_fmt_time}.jpg')
        self.folder = os.path.join(
            TMP_FOLDER,
            TMP_FOLDER_PREFIX + get_salt()
        )
        if os.path.exists(self.folder):
            shutil.rmtree(self.folder)
        os.makedirs(self.folder)
        image_file.download(self.path)
        self._start_date = date.today()

    def clear(self):
        if self.folder:
            shutil.rmtree(self.folder)
        self.__init__()


current_image = Image()


def get_salt(size=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def edit_save(update, context):
    text = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Понятно, {text}',
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
def image_loader(update, context):
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
        text='Загружен файл: {}'.format(text)
    )
    if not text.startswith('JPEG'):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Это не JPEG файл. Отмена.'
        )
        current_image.clear()
        return ConversationHandler.END
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='До какой даты или на какой срок сохранить картинку?'
    )
    return TEXT


image_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.document, image_loader)],
    states={
        TEXT: [MessageHandler(Filters.text, edit_save)],
    },
    fallbacks=[CommandHandler('echo', echo)],
)
