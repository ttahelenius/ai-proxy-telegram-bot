import pytest

from ..formatters import PartitionFormatter, ChainedPartitionFormatter, ReplyFormatter
from ..query_impl.deepseek import DeepSeekQuery
from .. import texts

class SimpleFormatter(PartitionFormatter):
    def __init__(self):
        super().__init__("<", ">")
    def in_format(self, s: str) -> str:
        return "|" + s + "|"
    def out_format(self, s: str) -> str:
        return s.upper()
formatter = SimpleFormatter()

def test_simple_formatter():
    assert formatter.format("testing <formatting>", affect_state=True) \
           == "TESTING |formatting|"
    assert formatter.format("<formatting> test", affect_state=True) \
           == "|formatting| TEST"
    assert formatter.format("String <to be formatted> contained", affect_state=True) \
           == "STRING |to be formatted| CONTAINED"
    
def test_simple_formatter_advancing():
    assert formatter.format("testing <formatting continues...", affect_state=True) \
           == "TESTING |formatting continues...|"
    assert formatter.format("...formatting continues> but ends here", affect_state=True) \
           == "|...formatting continues| BUT ENDS HERE"

def test_simple_formatter_not_advancing():
    assert formatter.format("testing <formatting continues...", affect_state=False) \
           == "TESTING |formatting continues...|"
    assert formatter.format("...formatting continues> but ends here", affect_state=False) \
           == "...FORMATTING CONTINUES> BUT ENDS HERE"
    
def test_chained_formatter():
    class CustomChainedPartitionFormatter(ChainedPartitionFormatter):
        def in_format(self, s: str) -> str:
            return "~" + s + "~"
    chained_formatter = CustomChainedPartitionFormatter(formatter, "[", "]")

    assert chained_formatter.format("testing <formatting>", affect_state=True) \
           == "TESTING |formatting|"
    
    assert chained_formatter.format("te[sting <formatting> te]st", affect_state=True) \
           == "TE~STING |formatting| TE~ST"
    
    assert chained_formatter.format("te[st]ing <for[matt]ing>", affect_state=True) \
           == "TE~ST~ING |for|~|matt|~|ing|"
    
    assert chained_formatter.format("te[]sti<ng >fo[r][m]<a[t]t>i][ng t>e<st", affect_state=True) \
           == "TESTI|ng |FO~R~~M~|a|~|t|~|t|I]~NG T>E|st|~"

def test_reply_formatter():
    reply_formatter = ReplyFormatter()

    assert reply_formatter.format("testing ```code``` test **bolding**") \
           == "testing ```\ncode\n``` test *bolding*"
    
    assert reply_formatter.format("Dots. ```in . code``` and in **bold.**") \
           == "Dots\. ```\nin \. code\n``` and in *bold\.*"
    
    assert reply_formatter.format("Bolding ```...**inside...** code```") \
           == "Bolding ```\n\.\.\.\*\*inside\.\.\.\*\* code\n```"
    
    assert reply_formatter.format("Bolding **outside ```...code``` block**") \
           == "Bolding *outside *```\n\.\.\.code\n``` block"
    
    assert reply_formatter.format("Alternating **bolding ```between** code``` block") \
           == "Alternating *bolding *```\nbetween\*\* code\n``` block"
    
    assert reply_formatter.format("Out ```of place` **symbols` *escaped** *inside``` both") \
           == "Out ```\nof place\` \*\*symbols\` \*escaped\*\* \*inside\n``` both"

def test_header_formatting():
    reply_formatter = ReplyFormatter()
    assert reply_formatter.format("# Heading\ntext") == "\n        __*Heading*__\n\ntext"
    assert reply_formatter.format("## Heading\ntext") == "\n    __*Heading*__\n\ntext"
    assert reply_formatter.format("### Heading\ntext") == "\n  __Heading__\n\ntext"
    assert reply_formatter.format("#### Heading\ntext") == "\n__Heading__\n\ntext"
    assert reply_formatter.format("# **Heading**\ntext") == "\n        __*Heading*__\n\ntext"
    assert reply_formatter.format("## **Heading**\ntext") == "\n    __*Heading*__\n\ntext"
    assert reply_formatter.format("### **Heading**\ntext") == "\n  __*Heading*__\n\ntext"
    assert reply_formatter.format("#### **Heading**\ntext") == "\n__*Heading*__\n\ntext"

    assert reply_formatter.format(" # Random\nHash signs ## won't\nGet ### interpreted\nas #### headings\n") \
            == " # Random\nHash signs ## won't\nGet ### interpreted\nas #### headings\n"

def test_link_formatting():
    reply_formatter = ReplyFormatter()
    assert reply_formatter.format("characters like [ escaped outside but [links](https://example.com) preserved.") \
            == "characters like \\[ escaped outside but [links](https://example\\.com) preserved\\."

def test_deepseek_formatter():
    deepseek_formatter = DeepSeekQuery.DeepSeekThinkFormatter()

    assert deepseek_formatter.format(
        "<think>thinking\na lot of\nthings\n```with code in between```\nbut still\nthinking!", finalized=False) \
           == texts.thinking + "\n>thinking\n>a lot of\n>things\n>```\n>with code in between\n>```\n>but still\n>thinking\!"

    assert deepseek_formatter.format(
        "<think>thinking\na lot of\nthings\n```with code in between```\nbut still\nthinking!", finalized=True) \
           == texts.thinking + "\n**>thinking\n>a lot of\n>things\n>```\n>with code in between\n>```\n>but still\n>thinking\!||"

def test_LaTeX_formatting():
    try:
        from pylatexenc.latex2text import LatexNodes2Text  # type: ignore

        reply_formatter = ReplyFormatter()

        assert reply_formatter.format("LaTeX formatted fraction \\frac{2}{3}") \
               == "LaTeX formatted fraction 2/3"

        assert reply_formatter.format(
            "LaTeX formatted outside code \\frac{2}{3} ```plaintext\nbut not inside \\frac{2}{3}```") \
               == "LaTeX formatted outside code 2/3 ```plaintext\n\nbut not inside \\\\frac\\{2\\}\\{3\\}\n```"
    except ImportError as e:
        pass