"""Finding code blocks in a message (#17)."""
from thechatplace.codeblocks import find_code_blocks, replace_code_blocks
from thechatplace.speech import strip_for_speech

TICKS = "`" * 3


def test_backtick_and_tilde_blocks_with_languages():
    text = (f"Intro\n{TICKS}python\ndef main():\n    pass\n{TICKS}\nMiddle\n"
            "~~~~\nplain\n~~~~\nEnd")
    blocks = find_code_blocks(text)
    assert [(b.language, b.code) for b in blocks] == [
        ("python", "def main():\n    pass"), ("", "plain")]
    assert blocks[0].describe() == "Code block, Python, 2 lines"
    assert blocks[0].row() == "Python, 2 lines: def main():"
    assert blocks[1].row() == "Code, 1 line: plain"


def test_closing_fence_must_match_and_be_long_enough():
    text = f"{TICKS}{TICKS[0]}md\n{TICKS}\nstill code\n~~~\n{TICKS}{TICKS[0]}\nafter"
    blocks = find_code_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].code == f"{TICKS}\nstill code\n~~~"


def test_unclosed_block_runs_to_the_end_and_inline_ticks_are_not_fences():
    assert find_code_blocks(f"See {TICKS}x{TICKS} inline") == []
    assert find_code_blocks(f"{TICKS}js x {TICKS}") == []
    blocks = find_code_blocks(f"Start\n{TICKS}sh\nls\nmore")
    assert [(b.language, b.code) for b in blocks] == [("sh", "ls\nmore")]


def test_replacing_blocks_keeps_the_other_lines():
    text = "a\n~~~\ncode\n~~~\nb"
    assert replace_code_blocks(text, lambda b: f"[{b.lines}]") == "a\n[1]\nb"
    assert strip_for_speech(text) == "a\n Code block omitted. \nb"


def test_fences_in_list_items_and_quotes_lose_their_indent():
    text = f"1. Install:\n\n    {TICKS}bash\n    pip install x\n      --pre\n    {TICKS}\n\n2. Run it"
    blocks = find_code_blocks(text)
    assert [(b.language, b.code) for b in blocks] == [("bash", "pip install x\n  --pre")]
    assert "2. Run it" in replace_code_blocks(text, lambda b: "X")
    quoted = f"> {TICKS}python\n> x = 1\n>     y = 2\n> {TICKS}\nafter"
    blocks = find_code_blocks(quoted)
    assert [(b.language, b.code) for b in blocks] == [("python", "x = 1\n    y = 2")]
    tabbed = f"\t{TICKS}\n\tcode\n\t{TICKS}\nafter"
    assert len(find_code_blocks(tabbed)) == 1


def test_a_fence_after_text_opens_a_block_and_the_closer_closes_it():
    text = f"Run this: {TICKS}python\nx=1\n{TICKS}\nafter"
    blocks = find_code_blocks(text)
    assert [(b.language, b.code) for b in blocks] == [("python", "x=1")]
    assert replace_code_blocks(text, lambda b: "X") == "Run this:\nX\nafter"


def test_crlf_and_strikethrough():
    blocks = find_code_blocks(f"{TICKS}python\r\nx=1\r\ny=2\r\n{TICKS}\r\n")
    assert blocks[0].code == "x=1\ny=2"
    assert find_code_blocks("~~~not code~~~ hmm\nmore") == []


def test_unclosed_block_hides_only_code_from_speech():
    assert strip_for_speech(f"Before\n{TICKS}\nsecret") == "Before\n Code block omitted."
