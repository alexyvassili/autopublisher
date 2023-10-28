import logging
import json
import traceback

import apiai
from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler
from telegram.ext import Filters

from telegramlib import owner_only
from customfilters import YandexCheckFilter
from autopublish import telegram_yandex_check
from mailbot import mail_handler
from imagebot import image_handler
from secrets import BOT_TOKEN, BOT_PROXY, DIALOGFLOW_API_CLIENT_TOKEN


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@owner_only
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет, хозяин!")


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


@owner_only
def yandex_check(update, context):
    link = update.message.text.strip()
    for msg in telegram_yandex_check(link):
        context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    context.bot.send_message(chat_id=update.effective_chat.id, text='Завершено!')


@owner_only
def dialog_bot(update, context):
    request = apiai.ApiAI(DIALOGFLOW_API_CLIENT_TOKEN).text_request()  # Токен API к Dialogflow
    request.lang = 'ru'  # На каком языке будет послан запрос
    # request.session_id = 'BatlabAIBot'  # ID Сессии диалога (нужно, чтобы потом учить бота)
    request.session_id = str(update.message.from_user.id)  # ID сессии диалога = ID пользователя
    request.query = update.message.text  # Посылаем запрос к ИИ с сообщением от юзера
    responseJson = json.loads(request.getresponse().read().decode('utf-8'))
    try:
        response = responseJson['result']['fulfillment']['speech']  # Разбираем JSON и вытаскиваем ответ
    except KeyError:
        response = "Недоступен dialogflow"
    # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
    response_text = response or 'Я Вас не совсем понял!'
    context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)


def any_answer(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='А больше я ничего и не умею!')


def error(update, context):
    """Log Errors caused by Updates."""
    logging.warning('Update "%s" caused error "%s"', update, context.error)
    tbc = traceback.format_exc()
    context.bot.send_message(chat_id=update.effective_chat.id, text='Произошла ошибка!')
    context.bot.send_message(chat_id=update.effective_chat.id, text=tbc)


start_handler = CommandHandler('start', start)
yandex_handler = MessageHandler(YandexCheckFilter(), yandex_check)
bot_handler = MessageHandler(Filters.text, dialog_bot)  # Текстики шлются в диалог бота
echo_handler = MessageHandler(Filters.text, echo)
any_handler = MessageHandler(Filters.all, any_answer)  # Заглушка на всё остальное


if __name__ == "__main__":
    updater = Updater(token=BOT_TOKEN, use_context=True, request_kwargs=BOT_PROXY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(mail_handler)
    dispatcher.add_handler(image_handler)
    dispatcher.add_handler(yandex_handler)
    dispatcher.add_handler(bot_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(any_handler)
    dispatcher.add_error_handler(error)

    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
