import telebot
from telebot import ContinueHandling
from telebot.formatting import escape_markdown
from telebot.types import Message  # type: ignore

from .texts import service_refused
from .query_impl.deepseek import DeepSeekR1Query
from .query_impl.google import GemmaQuery
from .query_impl.openai import OpenAIGPTQuery, OpenAIO1Query
from .query_impl.mistralai import MistralQuery
from .util import get_service_refuser
from .query import handle_query


def register(bot: telebot.TeleBot):
    service_refuser = get_service_refuser()

    query_implementations = [DeepSeekR1Query(), OpenAIGPTQuery(), OpenAIO1Query(), MistralQuery(), GemmaQuery()]

    @bot.message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
    @bot.edited_message_handler(func=lambda m: True, content_types=["text", "photo", "sticker"])
    def handle_message(msg: Message):
        if msg.any_text is None:
            return ContinueHandling()
        for query in query_implementations:
            if query.is_configured():
                prompt = query.matches(msg.any_text)
                if prompt is None:
                    continue
                if service_refuser.refuse(msg):
                    bot.send_message(msg.chat.id, escape_markdown(service_refused),
                                     reply_to_message_id=msg.id)
                    continue
                handle_query(bot, prompt, msg, query)
                break
        return ContinueHandling()