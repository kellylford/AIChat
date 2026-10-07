"""Finding code blocks in a message (#17)."""
from theclaudehub.codeblocks import find_code_blocks, replace_code_blocks
from theclaudehub.speech import strip_for_speech

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
