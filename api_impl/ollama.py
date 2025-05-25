from telebot.formatting import mcite # type: ignore

from ..query import ApiImplementations, TextGenQuery
from ..formatters import ChainedPartitionFormatter, ReplyFormatter
from .. import texts
from ..config import Feature
import json
import re

def bind(api_implementations: ApiImplementations):
    api_implementations.bind("Ollama", Feature.TEXT_GENERATION, lambda: OllamaQuery())

class OllamaQuery(TextGenQuery):
    class ThinkFormatter(ChainedPartitionFormatter):
        def __init__(self):
            super().__init__(ReplyFormatter(), "<think>", "</think>")
            self.finalized = False
            self.deepseek_thinking_first = True

        def reset(self):
            self.deepseek_thinking_first = True
            super().reset()

        def in_format(self, s: str) -> str:
            prefix = ""
            if self.deepseek_thinking_first:
                prefix = texts.thinking + "\n"
            if s and s.strip():
                return prefix + mcite(s, expandable=self.finalized, escape=False)
            return s

        def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
            self.finalized = finalized
            value = super().format(s, affect_state, finalized)
            if self.deepseek_thinking_first and affect_state:
                self.deepseek_thinking_first = False
            return value

    def __init__(self):
        super().__init__(OllamaQuery.ThinkFormatter())
        self.think_parser = re.compile("^(?:<think>.*?</think>)?(.*)$", flags=re.S)

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id)}
                          | {"stream": self.stream}
                          | self.params)

    def get_response_text(self, s: str) -> str:
        return json.loads(s)["message"]["content"]

    def transform_reply_for_history(self, reply: str) -> str:
        m = self.think_parser.match(reply)
        if m is not None:
            return m.group(1)
        return reply

    def history_printer(self, l):
        return [self.print_input(r, t, i) for (r, t, i) in l]

    @staticmethod
    def print_input(role, text, image):
        if image:
            return {"role": role, "content": text, "images": [image]}
        return {"role": role, "content": text}