from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore
from telebot.formatting import escape_markdown, mcite  # type: ignore
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
        def __init__(self, query, history_printer):
            self.query = query
            self.history_printer = history_printer
            self._history = {}
            self.id_table = {}

        def record(self, text: str, ids: list[int], reply_to_id: int | None, image_url: str | None = None):
            for id in ids:
                if id != ids[0]:
                    self.id_table[id] = ids[0]
            if image_url and self.query.image_url_in_base64:
                r = requests.get(image_url)
                if r.ok:
                    image_url = base64.b64encode(r.content).decode('utf-8')
            self._history[ids[0]] = self.query.transform_reply_for_history(text), image_url, reply_to_id

        def _normalize_id(self, id: int) -> int:
            tabled = self.id_table.get(id, None)
            return tabled if tabled is not None else id

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

    def __init__(self, formatter: Formatter = ReplyFormatter(),
                 history_printer = lambda l: [{"role": r, "content": t} for (r, t, i) in l],  # type: ignore
                 image_url_in_base64: bool = False):
        command = self.get_command()
        self.regex = None if command is None else f"^{command} ((.+\n*.*)+)$"
        self.url = config.get(self.get_vendor(), "Url")
        self.token = config.get(self.get_vendor(), "Token")
        self.model = config.get(self.get_vendor(), self.get_model())
        self.formatter = formatter
        self._history_printer = history_printer
        self.image_url_in_base64 = image_url_in_base64
        self._histories: dict[int, Query.History] = {}
        self.headers = {"Content-Type": "application/json"} | ({"Authorization": "Bearer " + self.token} if self.token else {})

    def matches(self, message: str) -> str | None:
        m = re.fullmatch(self.regex, message, flags=re.I)
        if m is None:
            return None
        return m.group(1)

    def get_command(self) -> str | None:
        raise NotImplementedError

    def get_vendor(self) -> str | None:
        raise NotImplementedError

    def get_model(self) -> str | None:
        raise NotImplementedError

    def is_configured(self):
        return self.regex and self.url and self.model

    def get_history(self, chat_id: int) -> History:
        history = self._histories.get(chat_id, None)
        if history is None:
            history = Query.History(self, self._history_printer)
            self._histories[chat_id] = history
        return history

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id)} | self.get_model_parameters())

    def get_model_parameters(self) -> dict[str, any]:
        return {}

    def get_response_text(self, s: str) -> str:
        return json.loads(s)["message"]["content"]

    def transform_reply_for_history(self, reply: str) -> str:
        return reply

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

        r = requests.post(query.url, data=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=True)

        parse_error = False
        raw = ""
        it = r.iter_lines(decode_unicode=True)
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
                    util.log_reply(query.get_vendor(), query.get_model(), total_reply, msg.chat.id)
                    return
            else:
                message_text = total_message + CONTINUATION_POSTFIX
                bot.edit_message_text(query.formatter.format(message_text, affect_state=True, finalized=True), msg.chat.id, bot_msg.message_id)
                if messages_left == 1:
                    bot.send_message(msg.chat.id, escape_markdown(texts.thats_enough), reply_to_message_id=msg.id)
                    query.get_history(msg.chat.id).record(total_reply, sent_message_ids, msg.id)
                    util.log_reply(query.get_vendor(), query.get_model(), total_reply, msg.chat.id)
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