from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore
from deepseek import DeepSeekQuery
from openai import ChatGPTQuery
from query import Query, handle_query
import config

bot = TeleBot(config.get_or_throw("TelegramBot", "Token"), parse_mode='MarkdownV2', num_threads=1)

deepseek = DeepSeekQuery()
chatgpt = ChatGPTQuery()

query_implementations: list[Query] = [deepseek, chatgpt]

@bot.edited_message_handler(func=lambda m: True, content_types = ["text", "photo", "sticker"])
@bot.message_handler(func=lambda m: True, content_types = ["text", "photo", "sticker"])
def handle_message(msg: Message):
    for query in query_implementations:
        if query.is_configured():
            if handle_query(bot, msg, query):
                return

bot.infinity_polling()