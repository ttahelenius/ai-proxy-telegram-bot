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

    def in_format(self, s: str) -> str:
        return s

    def out_format(self, s: str) -> str:
        return s

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        formatted, inside = format(s, self.begin_delimiter, self.end_delimiter,
                                   self.in_format, self.out_format, self.currently_inside)
        if affect_state:
            self.currently_inside = inside
        return formatted


class ChainedPartitionFormatter(Formatter):
    class InnerFormatter(PartitionFormatter):
        def __init__(self, begin_delimiter: str, end_delimiter: str, outer, next: Formatter, inside_not_chained: bool):
            super().__init__(begin_delimiter, end_delimiter)
            self.next = next
            self.outer = outer
            self.inside_not_chained = inside_not_chained
            self.affect_state = False

        def in_format(self, s: str) -> str:
            if s and s.strip():
                if self.inside_not_chained:
                    return self.outer.in_format(s)
                else:
                    return self.outer.in_format(self.next.format(s, self.affect_state))
            return s

        def out_format(self, s: str) -> str:
            return self.next.format(self.outer.out_format(s), self.affect_state)

        def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
            self.affect_state = affect_state
            return super().format(s, affect_state, finalized)

    def __init__(self, next: Formatter, begin_delimiter: str, end_delimiter: str, inside_not_chained: bool = False):
        self.inner = ChainedPartitionFormatter.InnerFormatter(begin_delimiter, end_delimiter, self, next, inside_not_chained)
        self.next = next
        self.reset()

    def reset(self):
        self.inner.reset()
        self.next.reset()

    def in_format(self, s: str) -> str:
        return s

    def out_format(self, s: str) -> str:
        return s

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return self.inner.format(s, affect_state, finalized)


class IdentityFormatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return s


try:
    from pylatexenc.latex2text import LatexNodes2Text # type: ignore

    class LaTeXFormatter(PartitionFormatter):
        def __init__(self):
            super().__init__("`", "`")

        def in_format(self, s: str) -> str:
            return "`" + s + "`"

        def out_format(self, s: str) -> str:
            return LatexNodes2Text().latex_to_text(s)

    latex_formatter = LaTeXFormatter()
except ImportError as e:
    latex_formatter = IdentityFormatter()



class EscapeFormatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return formatting.escape_markdown(s)

escape_formatter = EscapeFormatter()


class CompoundFormatter(Formatter):
    def __init__(self, *formatters: Formatter):
        self.formatters = formatters

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        for formatter in self.formatters:
            s = formatter.format(s, affect_state, finalized)
        return s


class H1Formatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return re.sub("^\\\\# ([^#\n]+)$", "\n" + " "*8 + "__*\g<1>*__\n", s, flags=re.M|re.S)

class H2Formatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return re.sub("^\\\\#\\\\# ([^#\n]+)$", "\n" + " "*4 + "__*\g<1>*__\n", s, flags=re.M|re.S)

class H3Formatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return re.sub("^\\\\#\\\\#\\\\# ([^#\n]+)$", "\n" + " "*2 + "__\g<1>__\n", s, flags=re.M|re.S)

class H4Formatter(Formatter):
    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return re.sub("^\\\\#\\\\#\\\\#\\\\# ([^#\n]+)$", "\n" + "__\g<1>__\n", s, flags=re.M|re.S)

header_formatter = CompoundFormatter(H1Formatter(), H2Formatter(), H3Formatter(), H4Formatter())


base_formatter = CompoundFormatter(escape_formatter, header_formatter)


class BoldFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(base_formatter, "**", "**")

    def in_format(self, s: str) -> str:
        return formatting.mbold(s, escape=False)

bold_formatter = BoldFormatter()


class CodeFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(bold_formatter, "```", "```", inside_not_chained=True)

    @staticmethod
    def substitute(m: re.Match[str]) -> str:
        language = m.group(1) or ""
        contents = m.group(2) or ""
        return "```" + formatting.escape_markdown(language) + "\n" + formatting.escape_markdown(contents) + "\n```"

    def in_format(self, s: str) -> str:
        return re.sub("^(\S+\n)?(.*)$", self.substitute, s, flags=re.S)

    def out_format(self, s: str) -> str:
        return latex_formatter.format(s)


class ReplyFormatter(CodeFormatter):
    pass
