import time
import logging
import json
import traceback

import telegram
import apiai
from telegram.ext import Updater, BaseFilter, Filters
from telegram.ext import CommandHandler, MessageHandler

from autopublisher import telegram_yandex_check, telegram_check
from telegramlib import owner_only
from secrets import BOT_TOKEN, BOT_PROXY, DIALOGFLOW_API_CLIENT_TOKEN


class YandexCheckFilter(BaseFilter):
    def filter(self, message):
        return 'https://yadi.sk/' in message.text.lower().strip()


class MailCheckFilter(BaseFilter):
    def filter(self, message):
        return 'проверь почту' in message.text.lower().strip()


class HelloFilter(BaseFilter):
    hi_messages = ["привет", "здоров"]

    def filter(self, message):
        msg = message.text.lower().strip()
        return any([text in msg for text in self.hi_messages])


def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))


def hello_msg(bot, update):
    update.message.reply_text(
        'Здорово, {}!'.format(update.message.from_user.first_name))


@owner_only
def start(bot, update):
    update.message.reply_text('Привет, хозяин!')


@owner_only
def mail_check(bot, update):
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    try:
        for msg in telegram_check():
            update.message.reply_text(msg)
    except Exception as e:
        tbc = traceback.format_exc()
        update.message.reply_text('Произошла ошибка! {}'.format(e))
        update.message.reply_text(tbc)
    else:
        update.message.reply_text('Завершено!')


@owner_only
def yandex_check(bot, update):
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    print(update.message.text)
    link = update.message.text.strip()
    try:
        for msg in telegram_yandex_check(link):
            update.message.reply_text(msg)
    except Exception as e:
        tbc = traceback.format_exc()
        update.message.reply_text('Произошла ошибка! {}'.format(e))
        update.message.reply_text(tbc)
    else:
        update.message.reply_text('Завершено!')


@owner_only
def dialog_bot(bot, update):
    request = apiai.ApiAI(DIALOGFLOW_API_CLIENT_TOKEN).text_request()  # Токен API к Dialogflow
    request.lang = 'ru'  # На каком языке будет послан запрос
    # request.session_id = 'BatlabAIBot'  # ID Сессии диалога (нужно, чтобы потом учить бота)
    request.session_id = str(update.message.from_user.id)  # ID сессии диалога = ID пользователя
    request.query = update.message.text  # Посылаем запрос к ИИ с сообщением от юзера
    responseJson = json.loads(request.getresponse().read().decode('utf-8'))
    response = responseJson['result']['fulfillment']['speech']  # Разбираем JSON и вытаскиваем ответ
    # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
    if response:
        update.message.reply_text(response)
        # bot.send_message(chat_id=update.message.chat_id, text=response)
    else:
        update.message.reply_text('Я Вас не совсем понял!')
        # bot.send_message(chat_id=update.message.chat_id, text='Я Вас не совсем понял!')


@owner_only
def any_answer(bot, update):
    update.message.reply_text('А больше я ничего и не умею!')


updater = Updater(token=BOT_TOKEN, request_kwargs=BOT_PROXY)

start_handler = CommandHandler('start', start)
hello_handler = CommandHandler('hello', hello)
mail_handler = MessageHandler(MailCheckFilter(), mail_check)
yandex_handler = MessageHandler(YandexCheckFilter(), yandex_check)
hello_msg_handler = MessageHandler(HelloFilter(), hello_msg)
bot_handler = MessageHandler(Filters.all, dialog_bot)  # Текстики (точнее сейчас всё) шлются в диалог бота
any_handler = MessageHandler(Filters.all, any_answer)  # Заглушка на всё остальное

updater.dispatcher.add_handler(start_handler)
updater.dispatcher.add_handler(hello_handler)
updater.dispatcher.add_handler(hello_msg_handler)
updater.dispatcher.add_handler(mail_handler)
updater.dispatcher.add_handler(yandex_handler)
updater.dispatcher.add_handler(bot_handler)
updater.dispatcher.add_handler(any_handler)

updater.start_polling()  # поехали!
