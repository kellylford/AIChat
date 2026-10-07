"""Finding the code blocks in a message (#17), to list, read and copy them.

A fenced block opens with three or more backticks or tildes (up to three
spaces in) and closes on a line of the same character, at least as long,
with nothing after it; an unclosed block runs to the end, as Markdown does.
The word after the opening fence is the language ("```python").
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Union

from .rendering import describe_code_block, language_name

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


@dataclass
class CodeBlock:
    language: str  # as written after the fence, "" if none
    code: str

    @property
    def lines(self) -> int:
        return len(self.code.rstrip("\n").split("\n")) if self.code.strip() else 0

    def describe(self) -> str:
        """"Code block, Python, 14 lines"."""
        return describe_code_block(self.language, self.code)

    def row(self) -> str:
        """"Python, 14 lines: def main(): …" for a list."""
        first = next((line.strip() for line in self.code.split("\n") if line.strip()), "")
        if len(first) > 80:
            first = first[:79] + "…"
        kind = language_name(self.language) or "Code"
        size = f"{self.lines} line{'s' if self.lines != 1 else ''}"
        return f"{kind}, {size}: {first}" if first else f"{kind}, {size}"


def find_code_blocks(text: str) -> List[CodeBlock]:
    return [part for part in _parts(text) if isinstance(part, CodeBlock)]


def replace_code_blocks(text: str, replace: Callable[[CodeBlock], str]) -> str:
    """``text`` with each code block, fences and all, replaced by
    ``replace(block)``, so everything that skips or describes code agrees on
    where the blocks are."""
    return "\n".join(part if isinstance(part, str) else replace(part)
                     for part in _parts(text))


def _parts(text: str) -> List[Union[str, CodeBlock]]:
    """The text's lines, with each code block's lines as one CodeBlock."""
    parts: List[Union[str, CodeBlock]] = []
    fence = ""
    language = ""
    lines: List[str] = []
    for line in (text or "").split("\n"):
        match = _FENCE.match(line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                    and not match.group(2).strip():
                parts.append(CodeBlock(language, "\n".join(lines)))
                fence, lines = "", []
            else:
                lines.append(line)
        elif match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            fence = match.group(1)
            info = match.group(2).strip().split()
            language = info[0] if info else ""
        else:
            parts.append(line)
    if fence:
        parts.append(CodeBlock(language, "\n".join(lines)))
    return parts
