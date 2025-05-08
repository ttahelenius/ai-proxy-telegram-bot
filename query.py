from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore
from telebot.formatting import escape_markdown, mcite  # type: ignore

from .config import Configuration
from .parsing import Formatter
from .formatters import ReplyFormatter
from .parsing import divide_to_before_and_after_character_limit
from . import util
from . import texts
from . import config
import json
import requests
import re
from time import time
from time import sleep
import base64

class Query:
    class History:
        def __init__(self, query: 'Query', history_printer, chat_id: int):
            self.query = query
            self.history_printer = history_printer
            self._history = {}
            self.id_table = {}
            self.chat_id = chat_id
            self._register_file_caching()
            self._load()

        def record(self, text: str, message_ids: list[int], reply_to_id: int | None, image_url: str | None = None):
            for message_id in message_ids:
                if message_id != message_ids[0]:
                    self.id_table[message_id] = message_ids[0]
            if image_url:
                r = requests.get(image_url)
                if r.ok:
                    image_url = base64.b64encode(r.content).decode('utf-8')
            self._history[message_ids[0]] = self.query.transform_reply_for_history(text), image_url, reply_to_id
            self._save()

        def _normalize_id(self, message_id: int) -> int:
            tabled = self.id_table.get(message_id, None)
            return tabled if tabled is not None else message_id

        def get(self, reply_to_id):
            l = []
            role = "user"
            while reply_to_id is not None:
                text, image_url, reply_to_id = self._history.get(self._normalize_id(reply_to_id), ("", None, None))
                if text != "":
                    l.append((role, text, image_url))
                    role = "user" if role == "assistant" else "assistant"
            l.reverse()
            return self.history_printer(l)

        @staticmethod
        def serialize(history: 'Query.History') -> str:
            return json.dumps(history.id_table) + '|' + json.dumps(history._history)

        @staticmethod
        def deserialize(serialized: str) -> tuple[dict[int, tuple[any]], dict[int, list[int]]]:
            id_table, history = serialized.split('|', maxsplit=1)
            return {int(k): tuple(v) for k, v in json.loads(history).items()}, {int(k): v for k, v in json.loads(id_table).items()}

        def _unique_identifier(self) -> str:
            return f'{self.query.__class__.__name__}_{self.query.command}_{self.chat_id}'

        def _register_file_caching(self):
            cacheable_chat_ids = config.get_int_list("TelegramBot", "ChatIDFilterForPersistentHistory")
            if cacheable_chat_ids is not None and self.chat_id in cacheable_chat_ids:
                filename = f'{self._unique_identifier()}.history'
                def save():
                    with open(filename, 'w+') as f:
                        f.write(Query.History.serialize(self))
                def load():
                    try:
                        with open(filename) as f:
                            self._history, self.id_table = Query.History.deserialize(f.read())
                    except FileNotFoundError:
                        pass
                self._save = save
                self._load = load
            else:
                self._save = lambda : None
                self._load = lambda : None

    def __init__(self, formatter: Formatter = ReplyFormatter()):
        self.command = None
        self.model = None
        self.url = None
        self.token = None
        self.stream = False
        self.params = None
        self.formatter = formatter
        self._history_printer = self.history_printer
        self._histories: dict[int, Query.History] = {}

    def history_printer(self, l):
        raise NotImplementedError

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        raise NotImplementedError

    def get_response_text(self, s: str) -> str:
        raise NotImplementedError

    def matches(self, message: str) -> str | None:
        m = re.fullmatch(f"^{self.command} ((.+\n*.*)+)$", message, flags=re.I)
        if m is None:
            return None
        return m.group(1)

    def is_configured(self):
        return self.command and self.url and self.model

    def get_history(self, chat_id: int) -> History:
        history = self._histories.get(chat_id, None)
        if history is None:
            history = Query.History(self, self._history_printer, chat_id)
            self._histories[chat_id] = history
        return history

    def transform_reply_for_history(self, reply: str) -> str:
        return reply

    @property
    def headers(self):
        return {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {self.token}"} if self.token else {})

    def configure(self, configuration: Configuration):
        self.model = configuration.model
        self.command = configuration.command
        self.url = configuration.url
        self.token = configuration.token
        self.stream = configuration.stream
        self.params = configuration.params

class NoMatchingApiImplementationFound(Exception):
    pass
class ApiConfigurationOverlap(Exception):
    pass

class ApiImplementations:
    def __init__(self):
        self.configs = dict()

    def bind(self, api: str, feature: str, generator):
        if (api, feature) in self.configs:
            raise ApiConfigurationOverlap()
        self.configs[(api, feature)] = generator

    def get(self, api: str, feature: str) -> Query:
        if (api, feature) not in self.configs:
            raise NoMatchingApiImplementationFound()
        return self.configs[(api, feature)]()

# Telegram limitations:
MAX_CHARACTERS_PER_MESSAGE = 4096
MIN_SECONDS_PER_UPDATE = 3

CONTINUATION_PREFIX = "...\n"
CONTINUATION_POSTFIX = "\n..."

def handle_query(bot: TeleBot, prompt: str, msg: Message, query: Query):
    r = None
    try:
        if msg.reply_to_message and msg.reply_to_message.any_text and msg.reply_to_message.from_user.id != bot.user.id:
            prompt = mcite(msg.reply_to_message.any_text) + "\n" + prompt

        image_url = get_image_url(bot, msg)

        query.get_history(msg.chat.id).record(prompt, [msg.id], msg.reply_to_message.id if msg.reply_to_message else None, image_url)

        bot_msg = bot.send_message(msg.chat.id, escape_markdown(texts.please_wait), reply_to_message_id=msg.id)

        sent_message_ids = [bot_msg.id]
        total_reply = ""
        total_message = ""
        last_update_time = time()
        messages_left = int(config.get_or_default("TelegramBot", "MaxMessagesPerReply", "9999"))
        query.formatter.reset()

        r = requests.post(query.url, data=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=query.stream)

        parse_error = False
        raw = ""
        it = r.iter_lines(decode_unicode=True) if query.stream else iter([r.text])
        while True:
            line = next(it, None)
            data_ended = line is None
            if not data_ended:
                if not line:
                    continue
                if isinstance(line, str):
                    raw += line
                if parse_error:
                    continue
                try:
                    response = query.get_response_text(line)
                    if response:
                        total_message += response
                        total_reply += response
                    if not response.strip():
                        continue
                except:
                    parse_error = True
                    continue

            if data_ended and parse_error:
                total_message = raw

            if time() - last_update_time <= MIN_SECONDS_PER_UPDATE:
                continue

            if not total_message.strip():
                bot.send_message(msg.chat.id, escape_markdown(texts.empty_reply))
                return

            limit = MAX_CHARACTERS_PER_MESSAGE - len(escape_markdown(CONTINUATION_POSTFIX))
            total_message, remainder = divide_to_before_and_after_character_limit(total_message, limit, query.formatter)
            if remainder == "":
                message_text = total_message + ("" if data_ended else CONTINUATION_POSTFIX)
                bot.edit_message_text(query.formatter.format(message_text, finalized=data_ended), msg.chat.id, bot_msg.message_id)
                if data_ended:
                    query.get_history(msg.chat.id).record(total_reply, sent_message_ids, msg.id)
                    util.log_reply(query.command, query.model, total_reply, msg.chat.id)
                    return
            else:
                message_text = total_message + CONTINUATION_POSTFIX
                bot.edit_message_text(query.formatter.format(message_text, affect_state=True, finalized=True), msg.chat.id, bot_msg.message_id)
                if messages_left == 1:
                    bot.send_message(msg.chat.id, escape_markdown(texts.thats_enough), reply_to_message_id=msg.id)
                    query.get_history(msg.chat.id).record(total_reply, sent_message_ids, msg.id)
                    util.log_reply(query.command, query.model, total_reply, msg.chat.id)
                    return
                messages_left -= 1
                bot_msg = bot.send_message(msg.chat.id, escape_markdown(texts.to_be_continued), reply_to_message_id=msg.id)
                sent_message_ids.append(bot_msg.id)
                total_message = CONTINUATION_PREFIX + remainder
                if data_ended:
                    sleep(MIN_SECONDS_PER_UPDATE)

            last_update_time = time()

    except Exception as e:
        error, _ = divide_to_before_and_after_character_limit(escape_markdown(str(e)), MAX_CHARACTERS_PER_MESSAGE)
        bot.send_message(msg.chat.id, error)
        raise e
    finally:
        if r:
            r.close()


def get_image_url(bot: TeleBot, msg: Message) -> str | None:
    if msg.photo:
        return bot.get_file_url(msg.photo[-1].file_id)

    if msg.reply_to_message and msg.reply_to_message.photo:
        return bot.get_file_url(msg.reply_to_message.photo[-1].file_id)

    if msg.reply_to_message and msg.reply_to_message.sticker:
        return bot.get_file_url(msg.reply_to_message.sticker.file_id)

    return None