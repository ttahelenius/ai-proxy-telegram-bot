import pytest

from parsing import CustomFormatter, ChainedFormatter, ReplyFormatter
from deepseek import DeepSeekQuery
import texts

class SimpleFormatter(CustomFormatter):
    def __init__(self):
        super().__init__(["<"], [">"])
    def in_format(self, s: str, advance_head: bool) -> str:
        return "|" + s + "|"
    def out_format(self, s: str, advance_head: bool) -> str:
        return s.upper()
formatter = SimpleFormatter()

def test_simple_formatter():
    assert formatter.format("testing <formatting>", advance_head=True) \
                         == "TESTING |formatting|"
    assert formatter.format("<formatting> test", advance_head=True) \
                         == "|formatting| TEST"
    assert formatter.format("String <to be formatted> contained", advance_head=True)  \
                         == "STRING |to be formatted| CONTAINED"
    
def test_simple_formatter_advancing():
    assert formatter.format("testing <formatting continues...", advance_head=True) \
                         == "TESTING |formatting continues...|"
    assert formatter.format("...formatting continues> but ends here", advance_head=True) \
                         == "|...formatting continues| BUT ENDS HERE"

def test_simple_formatter_not_advancing():
    assert formatter.format("testing <formatting continues...", advance_head=False) \
                         == "TESTING |formatting continues...|"
    assert formatter.format("...formatting continues> but ends here", advance_head=False) \
                         == "...FORMATTING CONTINUES> BUT ENDS HERE"
    
def test_chained_formatter():
    class CustomChainedFormatter(ChainedFormatter):
        def in_format(self, s: str) -> str:
            return "~" + s + "~"
    chained_formatter = CustomChainedFormatter(formatter, ["["], ["]"])

    assert chained_formatter.format("testing <formatting>", advance_head=True) \
                                 == "TESTING |formatting|"
    
    assert chained_formatter.format("te[sting <formatting> te]st", advance_head=True) \
                                 == "TE~STING |formatting| TE~ST"
    
    assert chained_formatter.format("te[st]ing <for[matt]ing>", advance_head=True) \
                                 == "TE~ST~ING |for|~|matt|~|ing|"
    
    assert chained_formatter.format("te[]sti<ng >fo[r][m]<a[t]t>i][ng t>e<st", advance_head=True) \
                                 == "TESTI|ng |FO~R~~M~|a|~|t|~|t|I]~NG T>E|st|~"

def test_reply_formatter():
    reply_formatter = ReplyFormatter()

    assert reply_formatter.format("testing ```code``` test **bolding**") \
                               == "testing ```\ncode``` test *bolding*"
    
    assert reply_formatter.format("Dots. ```in . code``` and in **bold.**") \
                               == "Dots\. ```\nin \. code``` and in *bold\.*"
    
    assert reply_formatter.format("Bolding ```...**inside...** code```") \
                               == "Bolding ```\n\.\.\.*inside\.\.\.* code```"
    
    assert reply_formatter.format("Bolding **outside ```...code``` block**") \
                               == "Bolding *outside *```\n\.\.\.code``` block"
    
    assert reply_formatter.format("Alternating **bolding ```between** code``` block") \
                               == "Alternating *bolding *```\nbetween* code*``` block"
    
    assert reply_formatter.format("Out ```of place` **symbols` *escaped** *inside``` both") \
                               == "Out ```\nof place\` *symbols\` \*escaped* \*inside``` both"
    
def test_deepseek_formatter():
    deepseek_formatter = DeepSeekQuery.DeepSeekThinkFormatter()

    assert deepseek_formatter.format("<think>thinking\na lot of\nthings\n```with code in between```\nbut still\nthinking!") \
                     == texts.thinking + "\n>thinking\n>a lot of\n>things\n>```\n>with code in between```\n>but still\n>thinking\!"