import warnings

from telebot import formatting

from .parsing import Formatter, format, format_matches
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
                    value = self.outer.in_format(s)
                else:
                    value = self.outer.in_format(self.next.format(s, self.affect_state))
                self.outer.previous_segment = s
                return value
            self.outer.previous_segment = s
            return s

        def out_format(self, s: str) -> str:
            value = self.next.format(self.outer.out_format(s), self.affect_state)
            self.outer.previous_segment = s
            return value

        def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
            self.affect_state = affect_state
            return super().format(s, affect_state, finalized)

    def __init__(self, next: Formatter, begin_delimiter: str, end_delimiter: str, inside_not_chained: bool = False):
        self.inner = ChainedPartitionFormatter.InnerFormatter(begin_delimiter, end_delimiter, self, next, inside_not_chained)
        self.next = next
        self.reset()
        self.previous_segment = ""

    def reset(self):
        self.inner.reset()
        self.next.reset()

    def in_format(self, s: str) -> str:
        return s

    def out_format(self, s: str) -> str:
        return s

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return self.inner.format(s, affect_state, finalized)


class MatchPartitionFormatter(Formatter):
    def __init__(self, pattern):
        self.pattern = pattern

    def in_format(self, s: str, match: re.Match) -> str:
        return s

    def out_format(self, s: str) -> str:
        return s

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return format_matches(s, self.pattern, self.in_format, self.out_format)


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
            return LatexNodes2Text(keep_comments=True).latex_to_text(s.replace("&", "\&"))

    latex_formatter = LaTeXFormatter()
except ImportError as e:
    warnings.warn("LaTeX -> Unicode formatting not available", stacklevel=2)
    latex_formatter = IdentityFormatter()



class EscapeFormatter(MatchPartitionFormatter):
    def __init__(self):
        super().__init__(r"\[([^[]+)\]\((https?://[^)]+)\)") # link

    def in_format(self, s: str, match: re.Match) -> str:
        return formatting.mlink(match.group(1), match.group(2))

    def out_format(self, s: str) -> str:
        return formatting.escape_markdown(s)

escape_formatter = EscapeFormatter()


class CompoundFormatter(Formatter):
    def __init__(self, *formatters: Formatter):
        self.formatters = formatters

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        for formatter in self.formatters:
            s = formatter.format(s, affect_state, finalized)
        return s


class BoldFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(escape_formatter, "**", "**")

    def in_format(self, s: str) -> str:
        return formatting.mbold(s, escape=False)

bold_formatter = BoldFormatter()

class H1Formatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(bold_formatter, "# ", "\n")
    def in_format(self, s: str) -> str:
        if not self.previous_segment or self.previous_segment.endswith("\n"):
            return "\n        __" + (s if '*' in s else "*" + s + "*") + "__\n\n"
        return "# " + s + "\n"
h1_formatter = H1Formatter()

class H2Formatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(h1_formatter, "## ", "\n")
    def in_format(self, s: str) -> str:
        if not self.previous_segment or self.previous_segment.endswith("\n"):
            return "\n    __" + (s if '*' in s else "*" + s + "*") + "__\n\n"
        return "## " + s + "\n"
h2_formatter = H2Formatter()

class H3Formatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(h2_formatter, "### ", "\n")
    def in_format(self, s: str) -> str:
        if not self.previous_segment or self.previous_segment.endswith("\n"):
            return "\n  __" + s + "__\n\n"
        return "### " + s + "\n"
h3_formatter = H3Formatter()

class H4Formatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(h3_formatter, "#### ", "\n")
    def in_format(self, s: str) -> str:
        if not self.previous_segment or self.previous_segment.endswith("\n"):
            return  "\n__" + s + "__\n\n"
        return "#### " + s + "\n"
h4_formatter = H4Formatter()

class CodeFormatter(ChainedPartitionFormatter):
    def __init__(self):
        super().__init__(h4_formatter, "```", "```", inside_not_chained=True)

    @staticmethod
    def substitute(m: re.Match[str]) -> str:
        language = m.group(1) or ""
        contents = m.group(2) or ""
        return "```" + formatting.escape_markdown(language) + "\n" + formatting.escape_markdown(contents) + "\n```"

    def in_format(self, s: str) -> str:
        return re.sub("^([^\s.]+\n)?(.*)$", self.substitute, s, flags=re.S)

    def out_format(self, s: str) -> str:
        return latex_formatter.format(s)


class ReplyFormatter(CodeFormatter):
    pass
