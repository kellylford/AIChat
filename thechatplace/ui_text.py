"""Text the UI shows that is worth testing without wx."""
from __future__ import annotations

import re
from typing import List

#: The window, in Tab order. The Help dialog and the README both describe it.
LAYOUT = (
    "One window, three parts, in Tab order: the session list; the messages of the "
    "loaded session; and the reply box with Send and Stop (for a Claude desktop app "
    "session, a read-only note, Open in Claude and Continue Here in the same place). "
    "Shift+Tab goes back the same way."
)

#: Every shortcut, grouped. The Help dialog and the README both list these.
SHORTCUTS = [
    ("Moving around", [
        ("Tab, Shift+Tab", "Session list, messages, reply box, and back"),
        ("Ctrl+1", "Go to the session list"),
        ("Ctrl+2", "Go to the messages"),
        ("Ctrl+3", "Go to the reply box (or the note, for a desktop session)"),
        ("F6, Shift+F6", "Next or previous part of the window: session list, messages, "
                         "reply box (when a session is loaded), status bar, and round again"),
        ("Ctrl+9", "Go to the status bar: what was last said, the loaded session, and "
                   "buttons for how full the context is, sessions that need you and an "
                   "update; Left and Right move between them, Tab leaves"),
        ("Escape in the messages or the reply box",
         "Back to the session list, on the same session"),
        ("Backspace in the messages", "Also back to the session list"),
    ]),
    ("Session list", [
        ("Enter", "Load that session and move to its messages"),
        ("Ctrl+O", "Open the selected session in the Claude desktop app"),
        ("Ctrl+N", "New Chat Place session"),
        ("Ctrl+Shift+N", "Continue the selected desktop app session here, as a copy you can "
                         "reply to (the desktop app session isn't changed)"),
        ("F5", "Refresh the list now and put it back in order (it also refreshes itself "
               "every few seconds, without moving rows while you're in it)"),
        ("Alt+V, O", "Sort Sessions: by status, newest first, oldest first, by title or "
                     "by folder; the choice is remembered"),
        ("Alt+V, H", "Show Sessions: all, needs you or working, needs you, desktop app, "
                     "Cowork, The Chat Place, Remote Control, ungrouped (in no group), "
                     "archived, or one of your groups"),
        ("Ctrl+E", "Export the selected (or loaded) session as Markdown, a web page or "
                   "plain text"),
        ("F2", "Rename the selected session (a desktop app session's new name shows only "
               "in The Chat Place)"),
        ("Applications key / Shift+F10", "The session's menu: load, open in Claude, rename, "
                                         "Remote Control, groups, export, hide or delete"),
        ("Alt+F, O", "Remote Control: reach the selected session from claude.ai and your "
                     "phone (a desktop app session can be continued here with it on)"),
        ("Ctrl+G", "Add the selected session to a group (or a new one); File, Remove "
                   "from Group and Manage Groups are on the File menu"),
        ("Delete", "Hide the selected session; View, Show Sessions, Hidden lists hidden "
                   "sessions, and File, Bring Back Session returns one"),
        ("Shift+Delete", "Delete one of The Chat Place's own sessions permanently, "
                         "transcript and all, after you confirm (desktop app sessions "
                         "can only be hidden)"),
        ("Ctrl+F", "Show only sessions whose title, folder or what they need contains some "
                   "text; Escape in the list shows them all again"),
    ]),
    ("Messages", [
        ("Enter, or Applications key / Shift+F10 then Read Full Message",
         "Read the whole message as a formatted page (move by heading, table, list and "
         "code block); Alt+P reads it as plain text instead; Escape comes back to it"),
        ("Ctrl+C", "Copy the whole message"),
        ("Ctrl+Shift+C", "Copy the message's last code block"),
        ("Ctrl+Enter on a queued message", "Send it now: Claude stops what it's doing and "
                                           "answers it"),
        ("Ctrl+Shift+B, or Applications key / Shift+F10 then Code Blocks",
         "List, read and copy each code block"),
        ("Ctrl+F, then F3 and Shift+F3", "Find a message containing some text (its whole "
                                         "text, not just the first line), then the next or "
                                         "previous one"),
        ("End", "Newest message"),
        ("Ctrl+T", "Show or hide tool activity"),
        ("Ctrl+O", "Open this session in the Claude desktop app"),
    ]),
    ("Reply box", [
        ("Ctrl+Enter", "Send (Chat Place sessions only); you stay in the reply box. "
                       "During a turn it queues the message and sends it when the turn ends"),
        ("Ctrl+Period", "Stop the running turn; a queued message goes back in the reply box"),
        ("Ctrl+/", "Insert a slash command or one of your skills (type to search); it goes at "
                   "the start of the reply box"),
        ("Ctrl+Shift+F", "Attach files or images to your next message (Attach Files button, "
                         "Alt+T); Delete in the attachments list removes one"),
        ("Ctrl+V with a picture copied", "Attach the picture (a screenshot from Win+Shift+S, "
                                         "say)"),
        ("Ctrl+Shift+M", "Other machines: list your sessions on other computers and send one "
                         "a message, through Claude in the loaded Chat Place session (it needs "
                         "Remote Control on)"),
        ("Ctrl+Shift+D", "Changed files: what Claude changed since your latest message or in "
         "the whole session; Enter on a file reads its changes line by line"),
        ("Ctrl+Shift+U", "Usage and context: a list of how full the loaded session's context "
                         "is, and how much of each of your plan's limits is used; Ctrl+C "
                         "copies a line"),
        ("Ctrl+Shift+T", "Turn status: how long Claude has been working, on what, "
                         "and whether a message is queued"),
    ]),
    ("Anywhere", [
        ("Ctrl+Shift+A", "Answer Claude: approve or deny a tool, answer its questions, or "
                         "approve its plan (the loaded session first, then the one that has "
                         "waited longest). Escape in the dialog answers later"),
        ("Ctrl+Shift+K", "What Claude knows about you: your instructions, memories, "
                         "skills, subagents, commands and settings, to read or open in "
                         "your editor"),
        ("F1", "This list of shortcuts"),
        ("Alt+H, G", "The user guide, read by heading"),
        ("Ctrl+Comma", "Settings (announcements and speech)"),
        ("Ctrl+Shift+R", "Repeat the last announcement"),
        ("Alt+F4", "Quit"),
    ]),
]


_HEADING = re.compile(r"^#{1,6}\s+", re.M)
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_EMPHASIS = re.compile(r"(\*\*|__)(.+?)\1")
_CODE = re.compile(r"`([^`]+)`")


def markdown_as_text(text: str) -> str:
    """A document's Markdown as plain text, for the text box (#104): Read as
    Plain Text, and the only view on a Mac. Headings lose their #s, bold and
    code lose their marks, and a link reads "text (address)", so a screen
    reader doesn't read out stars and brackets."""
    text = _HEADING.sub("", text)
    text = _LINK.sub(lambda m: m.group(1) if m.group(1) == m.group(2)
                     else f"{m.group(1)} ({m.group(2)})", text)
    text = _EMPHASIS.sub(r"\2", text)
    return _CODE.sub(r"\1", text)


def shortcuts_html() -> str:
    """The same list as a page body: a heading and a table per group, with
    the keys as row headers, so a screen reader moves by heading (H) and
    reads each key with what it does as it moves through a table."""
    import html

    parts = ["<h1>Keyboard shortcuts</h1>", f"<p>{html.escape(LAYOUT)}</p>"]
    for number, (group, items) in enumerate(SHORTCUTS, start=1):
        # The table takes its name from the heading above it, so the group
        # is named once, not as a heading and again as a separate label.
        parts.append(f'<h2 id="group{number}">{html.escape(group)}</h2>')
        parts.append(f'<table aria-labelledby="group{number}">'
                     '<thead><tr><th scope="col">Keys</th><th scope="col">What it does</th>'
                     "</tr></thead><tbody>")
        for key, action in items:
            parts.append(f'<tr><th scope="row">{html.escape(key)}</th>'
                         f"<td>{html.escape(action)}</td></tr>")
        parts.append("</tbody></table>")
    return "\n".join(parts)


def shortcuts_text() -> str:
    lines: List[str] = [LAYOUT, ""]
    for group, items in SHORTCUTS:
        lines.append(f"{group}:")
        for key, action in items:
            lines.append(f"  {key}: {action}")
        lines.append("")
    return "\n".join(lines).rstrip()
