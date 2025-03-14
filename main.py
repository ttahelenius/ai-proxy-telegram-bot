from telebot import TeleBot # type: ignore
from telebot.formatting import escape_markdown
from telebot.types import Message # type: ignore

import texts
from deepseek import DeepSeekR1Query
from google import GemmaQuery
from openai import OpenAIGPTQuery, OpenAIO1Query
from mistralai import MistralQuery
from util import override_background_instance_temporarily, get_service_refuser, setup_logging
from query import handle_query
import config
import pathlib
import sys

this_file = pathlib.Path(__file__).absolute().as_posix()

import logging

if __name__ == "__main__":
    try:
        override_background_instance_temporarily(this_file, test_mode="--test" in sys.argv)

        bot = TeleBot(config.get_or_throw("TelegramBot", "Token"), parse_mode='MarkdownV2', num_threads=1)

        setup_logging()

        service_refuser = get_service_refuser()

        query_implementations = [DeepSeekR1Query(), OpenAIGPTQuery(), OpenAIO1Query(), MistralQuery(), GemmaQuery()]

        @bot.message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
        @bot.edited_message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
        def handle_message(msg: Message):
            if msg.any_text is None:
                return
            for query in query_implementations:
                if query.is_configured():
                    prompt = query.matches(msg.any_text)
                    if prompt is None:
                        continue
                    if service_refuser.refuse(msg):
                        bot.send_message(msg.chat.id, escape_markdown(texts.service_refused), reply_to_message_id=msg.id)
                        continue
                    handle_query(bot, prompt, msg, query)
                    return

        bot.infinity_polling()
    except Exception as e:
        logging.exception(str(e), exc_info=True)