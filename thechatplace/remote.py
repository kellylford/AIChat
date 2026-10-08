"""Sessions on your other computers, reached through Claude (#123).

What's possible, from the research on #123: a Claude Code session with Remote
Control on can list your sessions on other machines (its ``ListAgents`` tool)
and send one a message (``SendMessage``). No documented API gives an app that
list directly, and nothing supported reads another machine's conversation. So
The Chat Place asks Claude, in one of its own sessions with Remote Control on:

* **The list** is read from the latest ``ListAgents`` result in that session's
  transcript, not from Claude's wording. Its format isn't a documented
  interface either, so it's parsed loosely: a line that doesn't look like a
  session is skipped, never an error.
* **Sending** is an ordinary turn asking Claude to pass your words on exactly.
  A reply comes back into the same session, shown as from that session.

No wx imports: everything here is testable on its own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

#: The tool whose result holds the list.
LIST_TOOL = "ListAgents"

#: A row of ListAgents: ``  Name [ref]  ·  Remote Control  ·  offline``. The
#: name may itself contain brackets or dots; the ref is the last bracketed hex.
_ROW = re.compile(r"^\s*(?P<name>.+?)\s+\[(?P<ref>[0-9A-Fa-f]{4,})\]\s*·\s*(?P<rest>.*)$")

#: Rows of this kind are sessions on other computers. Sessions on this one
#: show as "Claude Desktop session" and are in The Chat Place's list already.
REMOTE_KIND = "Remote Control"

LIST_PROMPT = (
    "Call ListAgents and tell me which of my Claude Code sessions on other computers "
    "(its Remote Control rows) there are: each one's name and whether it's idle, busy "
    "or offline. Don't send any of them a message.")


@dataclass(frozen=True)
class RemoteSession:
    name: str
    ref: str
    kind: str = REMOTE_KIND
    state: str = ""

    def address(self, unique: bool = True) -> str:
        """What SendMessage takes: the bare name, or with its ref when another
        row has the same name."""
        return self.name if unique else f"{self.name} [{self.ref}]"

    def describe(self) -> str:
        """One line for the list. "Offline" often only means between turns, so
        it's said as it is, not used to hide the session."""
        state = spoken_state(self.state)
        return f"{self.name}, {state}" if state else self.name


#: ListAgents states in words a screen reader says well.
_STATES = {"requires_action": "needs you", "running": "working", "busy": "working"}


def spoken_state(state: str) -> str:
    state = (state or "").strip()
    return _STATES.get(state.lower(), state.replace("_", " "))


def parse_list(text: str) -> List[RemoteSession]:
    """The Remote Control sessions in a ListAgents result, in its order."""
    sessions: List[RemoteSession] = []
    for line in (text or "").splitlines():
        if line.lstrip().lower().startswith("this session is"):
            continue  # the session doing the listing
        match = _ROW.match(line)
        if not match:
            continue
        parts = [p.strip() for p in match.group("rest").split("·")]
        kind = parts[0] if parts else ""
        if kind != REMOTE_KIND:
            continue
        state = parts[1] if len(parts) > 1 else ""
        name = " ".join(match.group("name").split())
        if name:
            sessions.append(RemoteSession(name, match.group("ref").lower(), kind, state))
    return sessions


def latest_list(tool_results: Iterable[str]) -> Optional[List[RemoteSession]]:
    """The newest ListAgents result among a session's tool results (as the
    transcript shows them: "ListAgents returned: ..."), parsed. None if the
    session has never listed them."""
    prefix = f"{LIST_TOOL} returned:"
    found = None
    for text in tool_results:
        if text.startswith(prefix):
            found = text[len(prefix):]
    return None if found is None else parse_list(found)


def addresses(sessions: List[RemoteSession]) -> List[str]:
    """Each session's address, with its ref only where a name is shared."""
    counts: dict = {}
    for s in sessions:
        counts[s.name] = counts.get(s.name, 0) + 1
    return [s.address(unique=counts[s.name] == 1) for s in sessions]


#: Around your words in the send prompt: not something a message would
#: contain by chance, as a line of ``---`` might.
FENCE_START, FENCE_END = "<<<MESSAGE", "MESSAGE>>>"


def send_prompt(address: str, message: str) -> str:
    """The turn that sends ``message`` to ``address``. Claude passes it on;
    the instructions ask for your words exactly, so it isn't reworded."""
    address = " ".join((address or "").replace('"', "'").split())
    return (f'Use SendMessage with to set to "{address}" to send the message between '
            f"{FENCE_START} and {FENCE_END} below, exactly as written, adding nothing. "
            f"Then tell me whether it was sent. Its reply, if any, will arrive here later.\n"
            f"{FENCE_START}\n{message.strip()}\n{FENCE_END}")
