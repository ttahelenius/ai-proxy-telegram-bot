from telebot.formatting import mcite # type: ignore
from query import Query
from parsing import ChainedFormatter, ReplyFormatter
import config
import texts
import json
import re

class DeepSeekQuery(Query):
	class DeepSeekThinkFormatter(ChainedFormatter):
		def __init__(self):
			super().__init__(ReplyFormatter(), ["<think>"], ["</think>"])

		def reset(self):
			self.deepseek_thinking_first = True
			super().reset()

		def in_format(self, s: str) -> str:
			prefix = ""
			if self.deepseek_thinking_first:
				prefix = texts.thinking + "\n"
			if s and s.strip():
				return prefix + mcite(s, escape=False)
			return s

		def format(self, str: str, advance_head: bool = False) -> str:
			value = super().format(str, advance_head)
			if self.deepseek_thinking_first and advance_head:
				self.deepseek_thinking_first = False
			return value

	def __init__(self):
		url = config.get("DeepSeek", "Url")
		model = config.get("DeepSeek", "Model")
		super().__init__("^r1 ((.+\n*.*)+)$", url, model, DeepSeekQuery.DeepSeekThinkFormatter())
		self.think_parser = re.compile("^(?:<think>(?:.*?)<\/think>)?(.*)$", flags=re.S)

	def get_data(self, chat_id: int, reply_to_id: int) -> str:
		return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id), "stream": True})
	
	def transform_reply_for_history(self, reply: str) -> str:
		m = self.think_parser.match(reply)
		if m is not None:
			return m.group(1)
		return reply