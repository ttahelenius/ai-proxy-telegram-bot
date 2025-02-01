from telebot import formatting

from parsing import Formatter, format
import re


class PartitionFormatter(Formatter):
    def __init__(self, begin_delimiter: str, end_delimiter: str):
        self.currently_inside = False
        self.begin_delimiter = begin_delimiter
        self.end_delimiter = end_delimiter
        self.reset()

    def reset(self):
        self.currently_inside = False

    def in_format(self, s: str, advance_head: bool) -> str:
        return s

    def out_format(self, s: str, advance_head: bool) -> str:
        return s

    def format(self, s: str, advance_head: bool = False) -> str:
        formatted, inside = format(s, self.begin_delimiter, self.end_delimiter,
                                   self.in_format, self.out_format, self.currently_inside, advance_head)
        if advance_head:
            self.currently_inside = inside
        return formatted


class ChainedPartitionFormatter(Formatter):
    class InnerFormatter(PartitionFormatter):
        def __init__(self, begin_delimiter: str, end_delimiter: str, outer, next: Formatter):
            super().__init__(begin_delimiter, end_delimiter)
            self.next = next
            self.outer = outer

        def in_format(self, s: str, advance_head: bool) -> str:
            if s and s.strip():
                return self.outer.in_format(self.next.format(s, advance_head))
            return s

        def out_format(self, s: str, advance_head: bool) -> str:
            return self.next.format(self.outer.out_format(s), advance_head)

    def __init__(self, next: Formatter, begin_delimiter: str, end_delimiter: str):
        self.inner = ChainedPartitionFormatter.InnerFormatter(begin_delimiter, end_delimiter, self, next)
        self.next = next
        self.reset()

    def reset(self):
        self.inner.reset()
        self.next.reset()

    def in_format(self, s: str) -> str:
        return s

    def out_format(self, s: str) -> str:
        return s

    def format(self, s: str, advance_head: bool = False) -> str:
        return self.inner.format(s, advance_head)


class IdentityFormatter(Formatter):
    def format(self, s: str, advance_head: bool = False) -> str:
        return s


try:
    from pylatexenc.latex2text import LatexNodes2Text # type: ignore

    class LaTeXFormatter(Formatter):
        def format(self, s: str, advance_head: bool = False) -> str:
            return LatexNodes2Text().latex_to_text(s)

    latex_formatter = LaTeXFormatter()
except ImportError as e:
    latex_formatter = IdentityFormatter()



class EscapeFormatter(Formatter):
    def format(self, s: str, advance_head: bool = False) -> str:
        return formatting.escape_markdown(s)

escape_formatter = EscapeFormatter()


class CompoundFormatter(Formatter):
    def __init__(self, *formatters: Formatter):
        self.formatters = formatters

    def format(self, s: str, advance_head: bool = False) -> str:
        for formatter in self.formatters:
            s = formatter.format(s, advance_head)
        return s

base_formatter = CompoundFormatter(escape_formatter)


class BoldFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(base_formatter, "**", "**")

    def in_format(self, s: str) -> str:
        return formatting.mbold(s, escape=False)

bold_formatter = BoldFormatter()


class CodeFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(bold_formatter, "```", "```")

    def in_format(self, s: str) -> str:
        return re.sub("^(\S+\n)?(.*)$", "```\g<1>\n\g<2>\n```", s, flags=re.S)

    def out_format(self, s: str) -> str:
        return latex_formatter.format(s)


class ReplyFormatter(CodeFormatter):
    pass
