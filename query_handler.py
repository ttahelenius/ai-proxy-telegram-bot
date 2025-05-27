import base64
from time import time, sleep

import requests
from requests import Response
from telebot import TeleBot
from telebot.formatting import escape_markdown, mcite
from telebot.types import Message

from AIProxyTelegramBot import config, texts, util
from AIProxyTelegramBot.parsing import divide_to_before_and_after_character_limit
from AIProxyTelegramBot.query import Query, Output, ContentType

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
        self.image = None
        self.image_base64 = None
        self.data_ended = False
        self.messages_left = int(config.get_or_default("TelegramBot", "MaxMessagesPerReply", "9999"))
        self.last_bot_msg = self.send_message(escape_markdown(texts.please_wait))
        self.sent_message_ids = [self.last_bot_msg.id]

    def send_message(self, message: str) -> Message:
        self.last_bot_msg = self.bot.send_message(self.msg.chat.id, message, reply_to_message_id=self.msg.id)
        self.messages_left -= 1
        return self.last_bot_msg

    def send_photo(self, image) -> Message:
        self.last_bot_msg = self.bot.send_photo(self.msg.chat.id, image, reply_to_message_id=self.msg.id)
        self.messages_left -= 1
        return self.last_bot_msg

    def send_document(self, document) -> Message:
        self.last_bot_msg = self.bot.send_document(self.msg.chat.id, document, reply_to_message_id=self.msg.id)
        self.messages_left -= 1
        return self.last_bot_msg

    def edit_last_message(self, message: str):
        self.bot.edit_message_text(message, self.msg.chat.id, self.last_bot_msg.message_id)

    def delete_last_message(self):
        self.bot.delete_message(self.msg.chat.id, self.last_bot_msg.message_id)

    def record_history(self, message=None, image_base64=None):
        if not self.query.transient_history:
            self.query.get_history(self.msg.chat.id).record(message, self.sent_message_ids, self.msg.id, image_base64)

    def register_text_reply(self, line) -> bool:
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
            return True

        limit = MAX_CHARACTERS_PER_MESSAGE - len(escape_markdown(CONTINUATION_POSTFIX))
        self.total_message, remainder = divide_to_before_and_after_character_limit(self.total_message, limit,
                                                                                   self.query.formatter)

        if remainder == "":
            message_text = self.total_message + ("" if self.data_ended else CONTINUATION_POSTFIX)
            self.edit_last_message(self.query.formatter.format(message_text, finalized=self.data_ended))
            if self.data_ended:
                self.record_history(message=self.total_reply)
                util.log_reply(self.query.command, self.query.model, self.total_reply, self.msg.chat.id)
                return True
        else:
            message_text = self.total_message + CONTINUATION_POSTFIX
            self.edit_last_message(self.query.formatter.format(message_text, affect_state=True, finalized=True))

            if self.messages_left == 1:
                self.send_message(escape_markdown(texts.thats_enough))
                self.record_history(message=self.total_reply)
                util.log_reply(self.query.command, self.query.model, self.total_reply, self.msg.chat.id)
                return True

            self.send_message(escape_markdown(texts.to_be_continued))
            self.sent_message_ids.append(self.last_bot_msg.id)
            self.total_message = CONTINUATION_PREFIX + remainder
        return False

    def register_image_reply(self, line) -> bool:
        response = self.query.get_response_image_base64(line)
        if response is None:
            return False
        self.image_base64 = response
        self.image = base64.b64decode(response)
        return True

    def process_image_reply(self) -> bool:
        if not self.image_base64:
            return True
        self.delete_last_message()
        photo_id = self.send_document(self.image)
        photo_compressed_id = self.send_photo(self.image)
        self.sent_message_ids = [photo_id.id, photo_compressed_id.id]
        self.record_history(image_base64=self.image_base64)
        return True


def handle(bot: TeleBot, prompt: str, msg: Message, query: Query):
    r = None
    try:
        if msg.reply_to_message and msg.reply_to_message.any_text and msg.reply_to_message.from_user.id != bot.user.id:
            prompt = mcite(msg.reply_to_message.any_text) + "\n" + prompt

        images_base64 = get_message_images(bot, msg)
        query.get_history(msg.chat.id).record(prompt, [msg.id], msg.reply_to_message.id if msg.reply_to_message else None, images_base64)

        handler = QueryHandler(bot, msg, query)

        r = http_post(msg, query)

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
                    if Output.IMAGE in query.output_types:
                        proceed = handler.register_image_reply(line)
                        if not proceed:
                            continue
                except:
                    parse_error = True
                    continue

            error_occurred = False
            if handler.data_ended and parse_error:
                handler.total_message = raw
                error_occurred = True

            if time() - last_update_time <= MIN_SECONDS_PER_UPDATE:
                continue

            if Output.TEXT in query.output_types or error_occurred:
                done = handler.process_text_reply()
                if done:
                    return
            if Output.IMAGE in query.output_types:
                done = handler.process_image_reply()
                if done:
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


def http_post(msg: Message, query: Query) -> Response:
    if query.get_content_type() == ContentType.FORM:
        return requests.post(query.url, files=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=query.stream)

    return requests.post(query.url, data=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=query.stream)


def get_message_images(bot: TeleBot, msg: Message) -> list[str]:
    images_base64 = []
    images_url = get_message_images_url(bot, msg)
    for image_url in images_url:
        r = requests.get(image_url)
        if r.ok:
            images_base64.append(base64.b64encode(r.content).decode('utf-8'))
    return images_base64


def get_message_images_url(bot: TeleBot, msg: Message) -> list[str]:
    images = []

    if msg.photo:
        images.append(bot.get_file_url(msg.photo[-1].file_id))

    if msg.reply_to_message and msg.reply_to_message.photo:
        images.append(bot.get_file_url(msg.reply_to_message.photo[-1].file_id))

    if msg.reply_to_message and msg.reply_to_message.sticker:
        images.append(bot.get_file_url(msg.reply_to_message.sticker.file_id))

    return images
