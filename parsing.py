from telebot import formatting # type: ignore

from pylatexenc.latex2text import LatexNodes2Text # type: ignore

class SkipToNext(Exception):
    pass

def format(str: str, begin_delimiters: list[str], end_delimiters: list[str],
           inside_formatter, outside_formatter, currently_inside: bool, advance_head: bool) -> tuple[str, bool]:
    if not str or not str.strip():
        return str, currently_inside
    result = ""
    inside = currently_inside
    inside_part = ""
    outside_part = ""
    skip_next_n = 0
    for i in range(0, len(str)):
        if skip_next_n > 0:
            skip_next_n -= 1
            continue
        try:
            for begin_delimiter in begin_delimiters:
                if str[i:i+len(begin_delimiter)] == begin_delimiter:
                    if not inside:
                        result += outside_formatter(outside_part, advance_head)
                        outside_part = ""
                        inside = True
                        skip_next_n = len(begin_delimiter)-1
                        raise SkipToNext
            for end_delimiter in end_delimiters:
                if str[i:i+len(end_delimiter)] == end_delimiter:
                    if inside:
                        result += inside_formatter(inside_part, advance_head)
                        inside_part = ""
                        inside = False
                        skip_next_n = len(end_delimiter)-1
                        raise SkipToNext
            if inside:
                inside_part += str[i]
            else:
                outside_part += str[i]
        except SkipToNext:
            continue
    if inside:
        result += inside_formatter(inside_part, advance_head)
    else:
        result += outside_formatter(outside_part, advance_head)
    return result, inside

class Formatter:
    def reset(self):
        pass

    def format(self, str: str, advance_head: bool = False) -> str:
        return str

class CustomFormatter(Formatter):
    def __init__(self, begin_delimiters: list[str], end_delimiters: list[str]):
        self.currently_inside = False
        self.begin_delimiters = begin_delimiters
        self.end_delimiters = end_delimiters
        self.reset()

    def reset(self):
        self.currently_inside = False

    def in_format(self, s: str, advance_head: bool) -> str:
        return s

    def out_format(self, s: str, advance_head: bool) -> str:
        return s

    def format(self, str: str, advance_head: bool = False) -> str:
        formatted, inside = format(str, self.begin_delimiters, self.end_delimiters, self.in_format, self.out_format, self.currently_inside, advance_head)
        if advance_head:
            self.currently_inside = inside
        return formatted


class ChainedFormatter(Formatter):
    class InnerFormatter(CustomFormatter):
        def __init__(self, begin_delimiters: list[str], end_delimiters: list[str], outer, next: Formatter):
            super().__init__(begin_delimiters, end_delimiters)
            self.next = next
            self.outer = outer

        def in_format(self, s: str, advance_head: bool) -> str:
            if s and s.strip():
                return self.outer.in_format(self.next.format(s, advance_head))
            return s

        def out_format(self, s: str, advance_head: bool) -> str:
            return self.next.format(s, advance_head)

    def __init__(self, next: Formatter, begin_delimiters: list[str], end_delimiters: list[str]):
        self.inner = ChainedFormatter.InnerFormatter(begin_delimiters, end_delimiters, self, next)
        self.next = next
        self.reset()

    def reset(self):
        self.inner.reset()
        self.next.reset()

    def in_format(self, s: str) -> str:
        return s

    def format(self, str: str, advance_head: bool = False) -> str:
        return self.inner.format(str, advance_head)


class EscapeFormatter(Formatter):
    def format(self, s: str, advance_head: bool = False) -> str:
        return formatting.escape_markdown(s)

class LaTeXFormatter(EscapeFormatter):
    def format(self, s: str, advance_head: bool = False) -> str:
        s = LatexNodes2Text().latex_to_text(s)
        return super().format(s, advance_head)

latex_formatter = LaTeXFormatter()

class BoldFormatter(ChainedFormatter):
    def __init__(self):
        super().__init__(latex_formatter, ["**"], ["**"])

    def in_format(self, s: str) -> str:
        return formatting.mbold(s, escape=False)
bold_formatter = BoldFormatter()

class CodeFormatter(ChainedFormatter):
    def __init__(self):
        super().__init__(bold_formatter, ["```python", "```C", "```cpp", "```c++", "```c#",
                                          "```csharp", "```java", "```bash", "```javascript",
                                          "```html", "```css", "```sql", "```xml", "```php",
                                          "```json", "```ini", "```typescript" "```kotlin",
                                          "```plaintext", "```"], ["```"])
    def in_format(self, s: str) -> str:
        return formatting.mcode(s, escape=False)

class ReplyFormatter(CodeFormatter):
    def __init__(self):
        super().__init__()


def divide_to_before_and_after_character_limit(s: str, limit: int, formatter: Formatter | None = None) -> tuple[str, str]:
    """
    Divides the given string into two parts: one of which length is at most the given limit and the rest.
    The string is split at the last space or line change if possible. If formatter is given, the formatted value
    is also ensured to fit into the limit, however only the unformatted value will be returned.

    Args:
        s (str): The string to be split.
        limit (int): The maximum number of characters in the string or its formatted value if formatter is given.
        formatter (Formatter): Formatter which if given, is used to format the string.

    Returns:
        tuple[str, str]: The given string split into a substring that fits the limit and the rest.
    """

    remainder = ""
    delimiter = ""
    while len(s) > limit or (formatter is not None and len(formatter.format(s)) > limit):
        if len(s) == 0:
            return s, remainder
        remainder = delimiter + remainder
        last_space = s.rfind(' ')
        last_line_change = s.rfind('\n')
        if last_space > last_line_change:
            delimiter = " "
            i = last_space
        else:
            delimiter = "\n"
            i = last_line_change
        if i == -1:
            delimiter = ""
            i = len(s)-1
        remainder = s[i+len(delimiter):] + remainder
        s = s[:i]
    return s, remainder