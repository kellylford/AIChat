"""Saving a session's conversation to a file (#33): Markdown, a web page,
or plain text.

Pure text, separate from the window, so it can be tested. Each message is a
heading ("You, 10:42" / "Claude, 10:43") and its text as written. A
message's own headings are moved down two levels, so the export's outline
stays session title, then message, then the message's sections, which is
what a screen reader moves through by heading. The web page uses the same
inert page as the formatted message view (nothing remote, no scripts).
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Iterable, List, Optional

from .rendering import html_page, markdown_to_html

MARKDOWN, HTML, TEXT = "md", "html", "txt"
#: (format, file dialog wildcard part), in the order the dialog offers them.
FORMATS = [
    (MARKDOWN, "Markdown (*.md)|*.md"),
    (HTML, "Web page (*.html)|*.html"),
    (TEXT, "Plain text (*.txt)|*.txt"),
]

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{1,6})(\s)")
_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def message_time(timestamp: str) -> str:
    """"10:42" (local time) from a transcript's ISO timestamp, or ""."""
    if not timestamp:
        return ""
    try:
        moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if moment.tzinfo is not None:
        moment = moment.astimezone()
    return moment.strftime("%H:%M")


def shift_headings(text: str, by: int = 2) -> str:
    """Markdown headings one level deeper per ``by`` (at most level 6),
    leaving code blocks alone."""
    lines = []
    fenced = False
    for line in (text or "").split("\n"):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            match = _HEADING.match(line)
            if match:
                level = min(len(match.group(1)) + by, 6)
                line = "#" * level + line[len(match.group(1)):]
        lines.append(line)
    return "\n".join(lines)


def default_filename(title: str, when: Optional[datetime] = None, extension: str = MARKDOWN) -> str:
    """"Fix the build 2026-10-07.md": the title made safe for a file name."""
    name = _UNSAFE_FILENAME.sub(" ", title or "Session")
    name = " ".join(name.split()).strip(" .")[:80] or "Session"
    return f"{name} {(when or datetime.now()).strftime('%Y-%m-%d')}.{extension}"


def _heading(message) -> str:
    when = message_time(getattr(message, "timestamp", ""))
    return f"{message.label}, {when}" if when else message.label


def _intro(title: str, folder: str, when: datetime) -> List[str]:
    lines = [f"Exported from TheClaudeHub on {when.strftime('%Y-%m-%d at %H:%M')}."]
    if folder:
        lines.append(f"Folder: {folder}")
    return lines


def to_markdown(title: str, messages: Iterable, folder: str = "",
                when: Optional[datetime] = None) -> str:
    when = when or datetime.now()
    parts = [f"# {title}", "", *[line + "  " for line in _intro(title, folder, when)], ""]
    for message in messages:
        parts += [f"## {_heading(message)}", "", shift_headings(message.text).rstrip(), ""]
    return "\n".join(parts).rstrip() + "\n"


def to_text(title: str, messages: Iterable, folder: str = "",
            when: Optional[datetime] = None) -> str:
    when = when or datetime.now()
    parts = [title, "=" * min(len(title), 70), *_intro(title, folder, when), ""]
    for message in messages:
        heading = _heading(message)
        parts += [heading, "-" * min(len(heading), 70), (message.text or "").rstrip(), ""]
    return "\n".join(parts).rstrip() + "\n"


def to_html(title: str, messages: Iterable, folder: str = "",
            when: Optional[datetime] = None) -> str:
    when = when or datetime.now()
    body = [f"<h1>{html.escape(title)}</h1>"]
    body += [f"<p>{html.escape(line)}</p>" for line in _intro(title, folder, when)]
    for number, message in enumerate(messages, start=1):
        body.append(f'<section aria-labelledby="m{number}">'
                    f'<h2 id="m{number}">{html.escape(_heading(message))}</h2>'
                    f"{markdown_to_html(shift_headings(message.text))}</section>")
    return html_page(title, "\n".join(body))


def render(fmt: str, title: str, messages: Iterable, folder: str = "",
           when: Optional[datetime] = None) -> str:
    messages = list(messages)
    if fmt == HTML:
        return to_html(title, messages, folder, when)
    if fmt == TEXT:
        return to_text(title, messages, folder, when)
    return to_markdown(title, messages, folder, when)
