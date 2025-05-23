import re

def format(s: str, begin_delimiter: str, end_delimiter: str,
           inside_formatter, outside_formatter, currently_inside: bool) -> tuple[str, bool]:
    if not s or not s.strip():
        return s, currently_inside
    result = ""
    inside = currently_inside
    inside_part = ""
    outside_part = ""
    skip_next_n = 0
    for i in range(0, len(s)):
        if skip_next_n > 0:
            skip_next_n -= 1
            continue
        if s[i:i + len(begin_delimiter)] == begin_delimiter:
            if not inside:
                result += outside_formatter(outside_part)
                outside_part = ""
                inside = True
                skip_next_n = len(begin_delimiter)-1
                continue
        if s[i:i + len(end_delimiter)] == end_delimiter:
            if inside:
                result += inside_formatter(inside_part)
                inside_part = ""
                inside = False
                skip_next_n = len(end_delimiter)-1
                continue
        if inside:
            inside_part += s[i]
        else:
            outside_part += s[i]
    if inside:
        result += inside_formatter(inside_part)
    else:
        result += outside_formatter(outside_part)
    return result, inside

def format_matches(s: str, pattern: str, inside_formatter, outside_formatter):
    result = ''
    last_end = 0
    for match in re.finditer(pattern, s):
        start, end = match.span()
        result += outside_formatter(s[last_end:start])
        result += inside_formatter(s[start:end], match)
        last_end = end
    result += outside_formatter(s[last_end:])
    return result


class Formatter:
    def reset(self):
        pass

    def format(self, s: str, affect_state: bool = False, finalized: bool = False) -> str:
        return s


def divide_to_before_and_after_character_limit(s: str, limit: int, formatter: Formatter | None = None) -> tuple[str, str]:
    """
    Divides the given string into two parts: one of which length is at most the given limit and the rest.
    The string is split at the last space or line change if possible. If no such characters are present or
    if such split would result in fewer characters than half the limit, then words will be broken.

    If formatter is given, the formatted value is also ensured to fit into the limit, however only the
    unformatted value will be returned.

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
        if i < (limit + 1) // 2: # If less than half the limit, reject
            i = -1
        if i == -1:
            delimiter = ""
            i = len(s)-1
        remainder = s[i+len(delimiter):] + remainder
        s = s[:i]
    return s, remainder