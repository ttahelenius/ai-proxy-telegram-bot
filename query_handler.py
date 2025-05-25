from time import time, sleep

import requests
from telebot import TeleBot
from telebot.formatting import escape_markdown, mcite
from telebot.types import Message

from AIProxyTelegramBot import config, texts, util
from AIProxyTelegramBot.parsing import divide_to_before_and_after_character_limit
from AIProxyTelegramBot.query import Query, Output

# Telegram limitations:
MAX_CHARACTERS_PER_MESSAGE = 4096
MIN_SECONDS_PER_UPDATE = 3

CONTINUATION_PREFIX = "...\n"
CONTINUATION_POSTFIX = "\n..."

class QueryHandler:
    def __init__(self, bot: TeleBot, msg: Message, query: Query):
        self.bot = bot
        self.msg = msg
        self.query = query
        self.query.formatter.reset()
        self.total_message = ""
        self.total_reply = ""
        self.data_ended = False
        self.messages_left = int(config.get_or_default("TelegramBot", "MaxMessagesPerReply", "9999"))
        self.last_bot_msg = self.send_message(escape_markdown(texts.please_wait))
        self.sent_message_ids = [self.last_bot_msg.id]

    def send_message(self, message: str) -> Message:
        self.last_bot_msg = self.bot.send_message(self.msg.chat.id, message, reply_to_message_id=self.msg.id)
        self.messages_left -= 1
        return self.last_bot_msg

    def edit_message(self, message: str):
        self.bot.edit_message_text(message, self.msg.chat.id, self.last_bot_msg.message_id)

    def register_text_reply(self, line):
        response = self.query.get_response_text(line)
        if response is None:
            self.total_message = None
        else:
            if response:
                self.total_message += response
                self.total_reply += response
            if not response.strip():
                return False
        return True

    def process_text_reply(self) -> bool:
        if not self.total_message.strip():
            self.bot.send_message(self.msg.chat.id, escape_markdown(texts.empty_reply))
            return False

        limit = MAX_CHARACTERS_PER_MESSAGE - len(escape_markdown(CONTINUATION_POSTFIX))
        self.total_message, remainder = divide_to_before_and_after_character_limit(self.total_message, limit,
                                                                                   self.query.formatter)

        if remainder == "":
            message_text = self.total_message + ("" if self.data_ended else CONTINUATION_POSTFIX)
            self.edit_message(self.query.formatter.format(message_text, finalized=self.data_ended))
            if self.data_ended:
                self.query.get_history(self.msg.chat.id).record(self.total_reply, self.sent_message_ids,
                                                                self.msg.id)
                util.log_reply(self.query.command, self.query.model, self.total_reply, self.msg.chat.id)
                return False
        else:
            message_text = self.total_message + CONTINUATION_POSTFIX
            self.edit_message(self.query.formatter.format(message_text, affect_state=True, finalized=True))

            if self.messages_left == 1:
                self.send_message(escape_markdown(texts.thats_enough))
                self.query.get_history(self.msg.chat.id).record(self.total_reply, self.sent_message_ids,
                                                                self.msg.id)
                util.log_reply(self.query.command, self.query.model, self.total_reply, self.msg.chat.id)
                return False

            self.send_message(escape_markdown(texts.to_be_continued))
            self.sent_message_ids.append(self.last_bot_msg.id)
            self.total_message = CONTINUATION_PREFIX + remainder
        return True


def handle(bot: TeleBot, prompt: str, msg: Message, query: Query):
    r = None
    try:
        if msg.reply_to_message and msg.reply_to_message.any_text and msg.reply_to_message.from_user.id != bot.user.id:
            prompt = mcite(msg.reply_to_message.any_text) + "\n" + prompt

        image_url = get_image_url(bot, msg)

        query.get_history(msg.chat.id).record(prompt, [msg.id], msg.reply_to_message.id if msg.reply_to_message else None, image_url)

        handler = QueryHandler(bot, msg, query)

        r = requests.post(query.url, data=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=query.stream)

        last_update_time = time()
        parse_error = False
        raw = ""
        it = r.iter_lines(decode_unicode=True) if query.stream else iter([r.text])
        while True:
            line = next(it, None)
            handler.data_ended = line is None
            if not handler.data_ended:
                if not line:
                    continue
                if isinstance(line, str):
                    raw += line
                if parse_error:
                    continue
                try:
                    if Output.TEXT in query.output_types:
                        proceed = handler.register_text_reply(line)
                        if not proceed:
                            continue
                except:
                    parse_error = True
                    continue

            if handler.data_ended and parse_error:
                handler.total_message = raw

            if time() - last_update_time <= MIN_SECONDS_PER_UPDATE:
                continue

            if Output.TEXT in query.output_types:
                proceed = handler.process_text_reply()
                if not proceed:
                    return

            if handler.data_ended:
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
