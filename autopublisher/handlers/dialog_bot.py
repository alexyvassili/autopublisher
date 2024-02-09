# from autopublisher.utils.telegram import owner_only


# @owner_only
# def dialog_bot(update, context):
#     request = apiai.ApiAI(DIALOGFLOW_API_CLIENT_TOKEN).text_request()  # Токен API к Dialogflow
#     request.lang = 'ru'  # На каком языке будет послан запрос
#     # request.session_id = 'BatlabAIBot'  # ID Сессии диалога (нужно, чтобы потом учить бота)
#     request.session_id = str(update.message.from_user.id)  # ID сессии диалога = ID пользователя
#     request.query = update.message.text  # Посылаем запрос к ИИ с сообщением от юзера
#     responseJson = json.loads(request.getresponse().read().decode('utf-8'))
#     try:
#         response = responseJson['result']['fulfillment']['speech']  # Разбираем JSON и вытаскиваем ответ
#     except KeyError:
#         response = "Недоступен dialogflow"
#     # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
#     response_text = response or 'Я Вас не совсем понял!'
#     context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)


# dialog_bot_handler = MessageHandler(Filters.text, dialog_bot)  # Текстики шлются в диалог бота
