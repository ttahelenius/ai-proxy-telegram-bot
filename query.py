from telebot import TeleBot # type: ignore
from telebot.types import Message # type: ignore
from telebot.formatting import escape_markdown # type: ignore
import json
import requests
import re
from time import time
from time import sleep
from parsing import Formatter, ReplyFormatter
from parsing import divide_to_before_and_after_character_limit
import texts
import config

class Query:
	class History:
		def __init__(self, query, history_printer):
			self.query = query
			self.history_printer = history_printer
			self._history = {}
			self.id_table = {}
		def record(self, text: str, ids: list[int], reply_to_id: int | None):
			for id in ids:
				if id != ids[0]:
					self.id_table[id] = ids[0]
			self._history[ids[0]] = self.query.transform_reply_for_history(text), reply_to_id
		def __normalize_id(self, id: int) -> int:
			tabled = self.id_table.get(id, None)
			return tabled if tabled is not None else id
		def get(self, reply_to_id):
			l = []
			role = "user"
			while reply_to_id is not None:
				text, reply_to_id = self._history.get(self.__normalize_id(reply_to_id), ("", None))
				if text != "":
					l.append((role, text))
					role = "user" if role == "assistant" else "assistant"
			l.reverse()
			return self.history_printer(l)

	def __init__(self, regex: str, url: str, model: str,
			  formatter: Formatter = ReplyFormatter(),
			  history_printer = lambda l: [{"role": r, "content": c} for (r, c) in l]): # type: ignore
		self.regex = regex
		self.model = model
		self.formatter = formatter
		self._history_printer = history_printer
		self._histories: dict[int, Query.History] = {}
		self.url = url
		self.headers: dict[str, str] | None = None

	def is_configured(self):
		return self.url and self.model

	def get_history(self, chat_id: int) -> History:
		history = self._histories.get(chat_id, None)
		if history is None:
			history = Query.History(self, self._history_printer)
			self._histories[chat_id] = history
		return history

	def get_data(self, chat_id: int, reply_to_id: int) -> str:
		return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id)})
	
	def get_response_text(self, str: str) -> str:
		return json.loads(str)["message"]["content"]
	
	def transform_reply_for_history(self, reply: str) -> str:
		return reply

# Telegram limitations:
character_limit = 4096
min_seconds_per_update = 3

continuation_prefix = "...\n"
continuation_postfix = "\n..."

def handle_query(bot: TeleBot, msg: Message, query: Query) -> bool:
	try:
		m = re.fullmatch(query.regex, msg.text, flags=re.I)
		if m is None:
			return False
		
		question = m.group(1)
		bot_msg = bot.send_message(msg.chat.id, escape_markdown(texts.please_wait), reply_to_message_id=msg.id)
		sent_message_ids = [bot_msg.id]
		query.get_history(msg.chat.id).record(question, [msg.id], msg.reply_to_message.id if msg.reply_to_message else None)
		r = requests.post(query.url, data=query.get_data(msg.chat.id, msg.id), headers=query.headers, stream=True)
		total_reply = ""
		total_message = ""
		last_update_time = time()
		messages_left = int(config.get_or_default("TelegramBot", "MaxMessagesPerReply", "9999"))
		query.formatter.reset()

		it = r.iter_lines(decode_unicode=True)
		while True:
			line = next(it, None)
			data_ended = line is None
			if not data_ended:
				if not line:
					continue
				response = query.get_response_text(line)
				if response:
					total_message += response
					total_reply += response
				if not response.strip():
					continue
			if time() - last_update_time <= min_seconds_per_update:
				continue
			if not total_message.strip():
				bot.send_message(msg.chat.id, escape_markdown(texts.empty_reply))
				return True
			limit = character_limit - len(escape_markdown(continuation_postfix))
			total_message, remainder = divide_to_before_and_after_character_limit(total_message, limit, query.formatter)
			if remainder == "":
				bot.edit_message_text(query.formatter.format(total_message + ("" if data_ended else continuation_postfix)), msg.chat.id, bot_msg.message_id)
				if data_ended:
					query.get_history(msg.chat.id).record(total_reply, sent_message_ids, msg.id)
					return True
			else:
				bot.edit_message_text(query.formatter.format(total_message + continuation_postfix, advance_head=True), msg.chat.id, bot_msg.message_id)
				if messages_left == 1:
					bot.send_message(msg.chat.id, escape_markdown(texts.thats_enough), reply_to_message_id=msg.id)
					query.get_history(msg.chat.id).record(total_reply, sent_message_ids, msg.id)
					return True
				messages_left -= 1
				bot_msg = bot.send_message(msg.chat.id, escape_markdown(texts.to_be_continued), reply_to_message_id=msg.id)
				sent_message_ids.append(bot_msg.id)
				total_message = continuation_prefix + remainder
				if data_ended:
					sleep(min_seconds_per_update)
			last_update_time = time()

	except Exception as e:
		error, _ = divide_to_before_and_after_character_limit(escape_markdown(str(e)), character_limit)
		bot.send_message(msg.chat.id, error)
		raise e