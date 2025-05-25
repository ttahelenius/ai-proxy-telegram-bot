from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore
from telebot.formatting import escape_markdown, mcite  # type: ignore

from .config import Configuration, Feature
from .parsing import Formatter
from .formatters import ReplyFormatter
from . import config
import json
import requests
import re
import base64
from enum import auto, Flag


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
        self.output_types = None
        self.formatter = formatter
        self._history_printer = self.history_printer
        self._histories: dict[int, Query.History] = {}

    def history_printer(self, l):
        raise NotImplementedError

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        raise NotImplementedError

    def get_response_text(self, s: str) -> str | None:
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
        self.output_types = Output.from_feature(configuration.feature)


class TextGenQuery(Query):
    def get_response_text(self, s: str) -> str | None:
        return None


class Output(Flag):
    TEXT = auto()

    @staticmethod
    def from_feature(feature: Feature) -> 'Output':
        if feature == Feature.TEXT_GENERATION:
            return Output.TEXT
        raise ValueError()


class NoMatchingApiImplementationFound(Exception):
    pass
class ApiConfigurationOverlap(Exception):
    pass


class ApiImplementations:
    def __init__(self):
        self.configs = dict()

    def bind(self, api: str, feature: Feature, generator):
        if (api, feature) in self.configs:
            raise ApiConfigurationOverlap()
        self.configs[(api, feature)] = generator

    def get(self, api: str, feature: Feature) -> Query:
        if (api, feature) not in self.configs:
            raise NoMatchingApiImplementationFound()
        return self.configs[(api, feature)]()