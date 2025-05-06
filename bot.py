import telebot
from telebot import ContinueHandling
from telebot.formatting import escape_markdown
from telebot.types import Message  # type: ignore

from . import api_impl
from .query import Query
from .texts import service_refused
from .util import get_service_refuser
from .query import handle_query, ApiImplementations
from .config import read_query_implementations

import importlib

def register(bot: telebot.TeleBot):
    service_refuser = get_service_refuser()

    query_implementations = get_query_implementations()

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


def get_query_implementations() -> list[Query]:
    query_implementations = []
    api_implementations = ApiImplementations()

    for module in api_impl.__all__:
        api = importlib.import_module(f'..api_impl.{module}', package=__name__)
        api.bind(api_implementations)

    for config in read_query_implementations():
        impl = api_implementations.get(config.api, config.feature)
        impl.configure(config)
        query_implementations.append(impl)

    return query_implementations