from telegram.ext import BaseFilter


class YandexCheckFilter(BaseFilter):
    def filter(self, message):
        return 'https://yadi.sk/' in message.text.lower().strip()
