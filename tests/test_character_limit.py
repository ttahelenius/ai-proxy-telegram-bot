import pytest

from parsing import Formatter
from parsing import divide_to_before_and_after_character_limit as divide

def test_typical():
    assert divide("some words\nin sequence", 16) == ("some words\nin", "sequence")
    assert divide("some words\nin sequence", 12) == ("some words", "in sequence")
    assert divide("some words\nin sequence", 8)  == ("some", "words\nin sequence")

def test_operation_not_needed():
    assert divide("some words\nin sequence", 22) == ("some words\nin sequence", "")
    assert divide("", 42) == ("", "")

def test_no_spaces():
    assert divide("abcd", 4) == ("abcd", "")
    assert divide("abcd", 3) == ("abc", "d")

def test_formatted():
    class LengtheningFormatter(Formatter):
        def format(self, s: str, advance_head: bool = False) -> str:
            return "E" + s
    class ShorteningFormatter(Formatter):
        def format(self, s: str, advance_head: bool = False) -> str:
            return s[1:]
    
    assert divide("a b c d e", 8) == ("a b c d", "e")
    assert divide("a b c d e", 9) == ("a b c d e", "")

    assert divide("a b c d e", 9,  LengtheningFormatter()) == ("a b c d", "e")
    assert divide("a b c d e", 10, LengtheningFormatter()) == ("a b c d e", "")

    assert divide("a b c d e", 8, ShorteningFormatter()) == ("a b c d", "e")
    assert divide("a b c d e", 9, ShorteningFormatter()) == ("a b c d e", "")

    assert divide("abcde", 4) == ("abcd", "e")
    assert divide("abcde", 5) == ("abcde", "")

    assert divide("abcde", 5,  LengtheningFormatter()) == ("abcd", "e")
    assert divide("abcde", 6, LengtheningFormatter()) == ("abcde", "")

    assert divide("abcde", 4, ShorteningFormatter()) == ("abcd", "e")
    assert divide("abcde", 5, ShorteningFormatter()) == ("abcde", "")