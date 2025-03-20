import pytest

from .. import parsing

in_format  = lambda s: "|" + s + "|"
out_format = lambda s: s.upper()

def format(s: str, begin_delimiter: str, end_delimiter: str, inside):
    return parsing.format(s, begin_delimiter, end_delimiter, in_format, out_format, inside)

def test_formatting_contained():
    assert format("testing <formatting>", "<", ">", inside=False) \
              == ("TESTING |formatting|", False)
    assert format("<formatting> test", "<", ">", inside=False) \
              == ("|formatting| TEST", False)
    assert format("String <to be formatted> contained", "<", ">", inside=False)  \
              == ("STRING |to be formatted| CONTAINED", False)

def test_formatting_to_be_continued():
    assert format("testing <formatting continues...", "<", ">", inside=False) \
              == ("TESTING |formatting continues...|", True)
    
def test_formatting_continued():
    assert format("...formatting continues> but ends here", "<", ">", inside=True) \
              == ("|...formatting continues| BUT ENDS HERE", False)
    
def test_complicated():
    assert format("<multiple><formatted> strings <of> characters", "<", ">", inside=False)  \
              == ("|multiple||formatted| STRINGS |of| CHARACTERS", False)
    assert format("formatting continues> but ends and <begins again", "<", ">", inside=True) \
              == ("|formatting continues| BUT ENDS AND |begins again|", True)
    
def test_pathological():
    assert format("out <in <still in> out > still out >>>><<in>< in <again> and empty: <>", "<", ">", inside=False)  \
              == ("OUT |in <still in| OUT > STILL OUT >>>>|<in|| in <again| AND EMPTY: ||", False)
    
def test_empty():
    assert format("", "<", ">", inside=True) \
              == ("", True)
    
def test_think_tags():
    assert format("<think>I'm thinking something</think> Ok so...", "<think>", "</think>", inside=False)  \
              == ("|I'm thinking something| OK SO...", False)
    assert format("<think>I'm having a loooong thought", "<think>", "</think>", inside=False)  \
              == ("|I'm having a loooong thought|", True)
    assert format("I've been thinking</think> but not anymore", "<think>", "</think>", inside=True)  \
              == ("|I've been thinking| BUT NOT ANYMORE", False)
    
def test_bolding():
    assert format("not bold **bolded** not bold", "**", "**", inside=False)  \
              == ("NOT BOLD |bolded| NOT BOLD", False)
    assert format("Not yet bold **but this is and continues", "**", "**", inside=False)  \
              == ("NOT YET BOLD |but this is and continues|", True)
    assert format("bolding continues** but ends here", "**", "**", inside=True)  \
              == ("|bolding continues| BUT ENDS HERE", False)