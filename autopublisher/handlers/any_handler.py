from telegram.ext import Filters, MessageHandler


def any_answer(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='А больше я ничего и не умею!')


any_handler = MessageHandler(Filters.all, any_answer)
