from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore

from deepseek import DeepSeekR1Query
from openai import OpenAIGPTQuery, OpenAIO1Query
from util import override_background_instance_temporarily
from query import Query, handle_query
import config
import pathlib

this_file = pathlib.Path(__file__).absolute().as_posix()


if __name__ == "__main__":
    override_background_instance_temporarily(this_file)

    bot = TeleBot(config.get_or_throw("TelegramBot", "Token"), parse_mode='MarkdownV2', num_threads=1)

    r1 = DeepSeekR1Query()
    chatgpt = OpenAIGPTQuery()
    o1 = OpenAIO1Query()

    query_implementations: list[Query] = [r1, chatgpt, o1]

    @bot.message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
    @bot.edited_message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
    def handle_message(msg: Message):
        for query in query_implementations:
            if query.is_configured():
                if handle_query(bot, msg, query):
                    return

    bot.infinity_polling()