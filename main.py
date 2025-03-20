from telebot import TeleBot # type: ignore

from . import bot
from . import config
from .util import setup_logging
import logging

if __name__ == "__main__":
    telebot = TeleBot(config.get_or_throw("TelegramBot", "Token"), parse_mode='MarkdownV2', num_threads=1)

    try:
        setup_logging()

        bot.register(telebot)

        telebot.infinity_polling()
    except Exception as e:
        logging.exception(str(e), exc_info=True)