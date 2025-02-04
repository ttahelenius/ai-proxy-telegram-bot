from telebot import TeleBot # type: ignore
from telebot.formatting import escape_markdown
from telebot.types import Message # type: ignore

import texts
from deepseek import DeepSeekR1Query
from openai import OpenAIGPTQuery, OpenAIO1Query
from util import override_background_instance_temporarily, get_service_refuser, setup_logging
from query import Query, handle_query
import config
import pathlib

this_file = pathlib.Path(__file__).absolute().as_posix()

import logging

if __name__ == "__main__":
    try:
        override_background_instance_temporarily(this_file)

        bot = TeleBot(config.get_or_throw("TelegramBot", "Token"), parse_mode='MarkdownV2', num_threads=1)

        setup_logging()

        service_refuser = get_service_refuser()

        r1 = DeepSeekR1Query()
        chatgpt = OpenAIGPTQuery()
        o1 = OpenAIO1Query()

        query_implementations: list[Query] = [r1, chatgpt, o1]

        @bot.message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
        @bot.edited_message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
        def handle_message(msg: Message):
            if service_refuser.refuse(msg):
                bot.send_message(msg.chat.id, escape_markdown(texts.service_refused), reply_to_message_id=msg.id)
                return
            for query in query_implementations:
                if query.is_configured():
                    if handle_query(bot, msg, query):
                        return

        bot.infinity_polling()
    except Exception as e:
        logging.exception(str(e), exc_info=True)