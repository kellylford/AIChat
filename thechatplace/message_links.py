"""The links in a session's messages (#190), for View, Links (Ctrl+L): a list
to open one in the browser, or copy it, without arrowing through the
conversation to find it.

A link is a Markdown link (``[words](address)``, an image's too), an address
in angle brackets, or a bare web address, in what you and Claude wrote. Links
in code (a fenced block or `inline code`) are listed too, marked as being in
code, since Claude often gives an address that way. Each address is listed
once, at its newest mention, newest first.

Only http, https and mailto links open, in the default browser, as the
formatted view's do (``rendering``), and links to sessions
(``thechatplace://session/<id>``, #144), which The Chat Place opens itself.
Anything else (a ``file:`` path, ``javascript:``) is listed so it can be
copied, and says why it won't open.

Nothing here imports wx, so it's all tested without a window.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .codeblocks import CodeBlock, split_code_blocks
from .links import is_app_link, parse_link
from .rendering import opens_in_browser

#: ``[words](address "title")`` and ``![alt](address)``. The address may be
#: in angle brackets, and may hold one level of parentheses (Wikipedia's).
_MARKDOWN = re.compile(r"!?\[([^\]\n]*)\]\(\s*<?((?:[^()\s<>]|\([^()\s]*\))+)>?"
                       r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)")
#: ``<https://example.com>`` and ``<mailto:me@example.com>``.
_ANGLE = re.compile(r"<((?:https?://|mailto:)[^<>\s]+)>", re.IGNORECASE)
#: A bare address: starts at a word boundary, runs to whitespace or a mark
#: that can't be in one. Trailing punctuation is trimmed afterwards.
_BARE = re.compile(r"(?<![\w/:@.-])((?:https?://|mailto:)[^\s<>\[\]\"'`]+)", re.IGNORECASE)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_TRAILING = ".,;:!?*_~'\""


@dataclass
class FoundLink:
    url: str
    #: The link's own words, "" for a bare address (or words that are just
    #: the address again).
    words: str
    #: Who wrote it, as the messages list says: "Claude", "You", "Tool"...
    who: str
    #: How many messages before the newest one it's in: 0 is the newest.
    ago: int
    in_code: bool = False

    @property
    def is_session_link(self) -> bool:
        return parse_link(self.url) is not None

    @property
    def can_open(self) -> bool:
        return opens_in_browser(self.url) or self.is_session_link

    def why_not(self) -> str:
        """Why it won't open, "" if it will."""
        if self.can_open:
            return ""
        if is_app_link(self.url):
            return "That link isn't one The Chat Place knows. It can only be copied."
        scheme = self.url.split(":", 1)[0].lower() if ":" in self.url else ""
        kind = f"A {scheme}: link" if scheme else "This link"
        return (f"{kind} isn't opened from here, only web and email links are. "
                "It can only be copied.")

    @property
    def address(self) -> str:
        """The address as it's read: without "https://", and a mail link as
        its address."""
        return _readable(self.url)

    def when(self) -> str:
        if self.ago == 0:
            return "the latest message"
        return "1 message ago" if self.ago == 1 else f"{self.ago} messages ago"

    def row(self) -> str:
        """"release notes, github.com/…/v0.1.5. Claude, 3 messages ago" for
        the list: the words, where it goes, who wrote it and roughly when."""
        said = f"{self.words}, {self.address}" if self.words else self.address
        notes = [f"{self.who}, {self.when()}"]
        if self.in_code:
            notes.append("in code")
        if not self.can_open:
            notes.append("copy only")
        return f"{said}. " + ", ".join(notes)

    def markdown(self) -> str:
        """The link as Markdown, to paste: ``[words](url)`` or ``<url>``."""
        if self.words:
            words = self.words.replace("[", "\\[").replace("]", "\\]")
            return f"[{words}]({self.url})"
        return f"<{self.url}>"


def _readable(url: str) -> str:
    lowered = url.lower()
    for prefix in ("https://", "http://"):
        if lowered.startswith(prefix):
            url = url[len(prefix):]
            break
    else:
        if lowered.startswith("mailto:"):
            return url[len("mailto:"):]
    return url[4:] if url.lower().startswith("www.") else url


def _trim(url: str) -> str:
    """A bare address without the punctuation after it: "(see https://x.y/a)."
    is https://x.y/a, but https://en.wikipedia.org/wiki/Foo_(bar) keeps its
    closing parenthesis."""
    while url:
        if url[-1] in _TRAILING:
            url = url[:-1]
        elif url[-1] == ")" and url.count(")") > url.count("("):
            url = url[:-1]
        else:
            break
    return url


def _words(words: str, url: str) -> str:
    words = " ".join(words.replace("`", "").replace("**", "").split())
    if not words or words == url or _readable(words) == _readable(url):
        return ""
    return words


def links_in_text(text: str) -> List[Tuple[str, str, bool]]:
    """(url, words, in code) for each link in ``text``, in order."""
    found: List[Tuple[int, str, str, bool]] = []
    offset = 0
    for part in split_code_blocks(text):
        if isinstance(part, CodeBlock):
            # In code, Markdown isn't Markdown: only bare addresses.
            for match in _BARE.finditer(part.code):
                url = _trim(match.group(1))
                if url:
                    found.append((offset + match.start(), url, "", True))
            offset += len(part.code) + 1
            continue
        line = part
        spans = [(m.start(), m.end()) for m in _INLINE_CODE.finditer(line)]

        def in_code(at: int) -> bool:
            return any(start <= at < end for start, end in spans)
        taken = list(line)
        for match in _MARKDOWN.finditer(line):
            url = match.group(2)
            if in_code(match.start()):
                continue  # `[x](y)` is shown as code; its address is found below
            found.append((offset + match.start(), url, _words(match.group(1), url), False))
            taken[match.start():match.end()] = " " * (match.end() - match.start())
        rest = "".join(taken)
        for match in _ANGLE.finditer(rest):
            found.append((offset + match.start(), match.group(1), "", in_code(match.start())))
            rest = rest[:match.start()] + " " * (match.end() - match.start()) + rest[match.end():]
        for match in _BARE.finditer(rest):
            url = _trim(match.group(1))
            if url:
                found.append((offset + match.start(), url, "", in_code(match.start())))
        offset += len(line) + 1
    found.sort(key=lambda item: item[0])
    return [(url, words, code) for _at, url, words, code in found]


def find_links(messages: Iterable) -> List[FoundLink]:
    """Every link in ``messages`` (oldest first, as the messages list has
    them; each has ``label`` and ``text``): the newest message's first, in
    the order they're written within a message, each address once, at its
    newest mention, with the words it had there (or, if it had none there,
    the newest words it had anywhere)."""
    messages = list(messages)
    newest = len(messages) - 1
    seen: dict = {}
    order: List[str] = []
    for index in range(newest, -1, -1):
        message = messages[index]
        for url, words, code in links_in_text(message.text or ""):
            key = url.rstrip("/") if opens_in_browser(url) else url
            link: Optional[FoundLink] = seen.get(key)
            if link is None:
                seen[key] = FoundLink(url, words, message.label, newest - index, code)
                order.append(key)
            elif not link.words and words:
                link.words = words
    return [seen[key] for key in order]


def matches(link: FoundLink, typed: str) -> bool:
    """Whether a link is kept by what's typed in the filter: every word, in
    its words, address or who wrote it."""
    haystack = f"{link.words} {link.url} {link.who}".lower()
    return all(word in haystack for word in typed.lower().split())
