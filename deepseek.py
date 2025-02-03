from telebot.formatting import mcite # type: ignore

import config
from query import Query
from formatters import ChainedPartitionFormatter, ReplyFormatter
import texts
import re

class DeepSeekQuery(Query):
    class DeepSeekThinkFormatter(ChainedPartitionFormatter):
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
        super().__init__(DeepSeekQuery.DeepSeekThinkFormatter())
        self.think_parser = re.compile("^(?:<think>.*?</think>)?(.*)$", flags=re.S)

    def get_vendor(self) -> str | None:
        return "DeepSeek"

    def get_model_parameters(self) -> dict[str, any]:
        return {"stream": True} | super().get_model_parameters()

    def transform_reply_for_history(self, reply: str) -> str:
        m = self.think_parser.match(reply)
        if m is not None:
            return m.group(1)
        return reply


class DeepSeekR1Query(DeepSeekQuery):
    def get_command(self) -> str | None:
        return "r1"
    def get_model(self) -> str | None:
        return "R1Model"
    def get_model_parameters(self) -> dict[str, any]:
        return config.get_key_value_pairs(self.get_vendor(), "R1Params") | super().get_model_parameters()