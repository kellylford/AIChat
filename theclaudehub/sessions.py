"""The session list: where its entries come from, their state, and their order.

Two sources:

* **Desktop app sessions**, from the Claude desktop app's metadata files
  (``local_<id>.json``). Read-only, always: TheClaudeHub never writes there.
* **TheClaudeHub's own sessions**, from its own store (``own_store``).

Live state comes from ``~/.claude/sessions/<pid>.json`` (``status`` busy or
idle) for desktop sessions, and from TheClaudeHub's own running turns for its
own sessions. The desktop app's ``postTurnSummary`` (``status_category``,
``needs_action``) decides "needs you" when present. All of it is undocumented,
so every field is read defensively and a file that will not parse is skipped.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from . import platform_paths

WORKING = "working"
NEEDS_YOU = "needs you"
IDLE = "idle"

_STATE_ORDER = {NEEDS_YOU: 0, WORKING: 1, IDLE: 2}

#: postTurnSummary.status_category values that mean "waiting on Kelly".
_NEEDS_YOU_CATEGORIES = {"blocked", "review_ready", "needs_input", "waiting",
                         "needs_action", "needs_you"}

DESKTOP = "desktop"
OWN = "own"


@dataclass
class SessionInfo:
    source: str                 # DESKTOP or OWN
    key: str                    # unique in the list: local_ id, or own:<cli id>
    title: str
    cwd: str
    cli_session_id: str         # transcript file name / --resume id
    desktop_session_id: str = ""  # local_... id for claude:// links ("" if none)
    last_activity_ms: int = 0
    state: str = IDLE
    detail: str = ""            # needs_action text, error, etc.
    permission_mode: str = ""
    unread: bool = False
    #: The desktop app archived it (shown only in the Archived view, #32).
    archived: bool = False
    #: The desktop app has linked it for Remote Control (claude.ai).
    remote: bool = False
    #: TheClaudeHub groups it's in (#31), set by the window, read in its row.
    groups: tuple = ()

    @property
    def is_own(self) -> bool:
        return self.source == OWN

    @property
    def repo(self) -> str:
        cwd = (self.cwd or "").rstrip("\\/")
        if not cwd:
            return "unknown folder"
        name = cwd.replace("\\", "/").split("/")[-1]
        # A worktree reads better as the repo it belongs to.
        parts = cwd.replace("\\", "/").split("/")
        if ".claude" in parts:
            index = parts.index(".claude")
            if index > 0 and index + 1 < len(parts) and parts[index + 1] == "worktrees":
                return f"{parts[index - 1]} worktree"
        return name

    @property
    def can_open_in_claude(self) -> bool:
        return bool(self.desktop_session_id)

    def list_line(self, now_ms: Optional[int] = None) -> str:
        """What a screen reader hears on arrowing to this session."""
        parts = [self.title or "Untitled session", self.repo]
        state = self.state
        if self.detail:
            state = f"{state}: {self.detail}"
        parts.append(state)
        if self.unread:
            parts.append("new reply")
        parts.append(describe_age(self.last_activity_ms, now_ms))
        if self.is_own:
            parts.append("TheClaudeHub session")
        if self.archived:
            parts.append("archived")
        if self.groups:
            parts.append(("group " if len(self.groups) == 1 else "groups ")
                         + ", ".join(self.groups))
        return ", ".join(parts)


def describe_age(then_ms: int, now_ms: Optional[int] = None) -> str:
    """'just now', '5 minutes ago', 'yesterday', '3 days ago'."""
    if not then_ms:
        return "no activity recorded"
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    seconds = max(0, (now_ms - then_ms) // 1000)
    if seconds < 60:
        return "active just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"active {minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"active {hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days == 1:
        return "active yesterday"
    if days < 30:
        return f"active {days} days ago"
    months = days // 30
    return f"active {months} month{'s' if months != 1 else ''} ago"


#: How the session list can be ordered (View, Sort Sessions): (value, menu label).
#: Within the same title or folder, newest comes first.
SORT_STATUS = "status"
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_TITLE = "title"
SORT_FOLDER = "folder"
SORT_ORDERS = [
    (SORT_STATUS, "By &Status (needs you, then working, then the rest)"),
    (SORT_NEWEST, "&Newest First"),
    (SORT_OLDEST, "&Oldest First"),
    (SORT_TITLE, "By &Title (A to Z)"),
    (SORT_FOLDER, "By &Folder (A to Z)"),
]
SORT_VALUES = [value for value, _label in SORT_ORDERS]
#: Said after choosing one: "Sessions sorted by title."
SORT_SPOKEN = {SORT_STATUS: "by status", SORT_NEWEST: "newest first",
               SORT_OLDEST: "oldest first", SORT_TITLE: "by title",
               SORT_FOLDER: "by folder"}


#: Which sessions the list shows (View, Show, #32): (value, menu label). A
#: group's view is "group:<name>".
VIEW_ALL = "all"
VIEW_ACTIVE = "active"
VIEW_NEEDS_YOU = "needs"
VIEW_DESKTOP = "desktop"
VIEW_OWN = "own"
VIEW_REMOTE = "remote"
VIEW_ARCHIVED = "archived"
GROUP_VIEW_PREFIX = "group:"
VIEWS = [
    (VIEW_ALL, "&All Sessions"),
    (VIEW_ACTIVE, "Needs You or &Working"),
    (VIEW_NEEDS_YOU, "&Needs You"),
    (VIEW_DESKTOP, "&Desktop App Sessions"),
    (VIEW_OWN, "&TheClaudeHub Sessions"),
    (VIEW_REMOTE, "&Remote Control Sessions"),
    (VIEW_ARCHIVED, "Ar&chived"),
]
#: Said and shown in the list's name: "showing needs you or working".
VIEW_SPOKEN = {VIEW_ALL: "all sessions", VIEW_ACTIVE: "needs you or working",
               VIEW_NEEDS_YOU: "needs you", VIEW_DESKTOP: "desktop app sessions",
               VIEW_OWN: "TheClaudeHub sessions", VIEW_REMOTE: "Remote Control sessions",
               VIEW_ARCHIVED: "archived sessions"}


def group_view(name: str) -> str:
    return GROUP_VIEW_PREFIX + name


def view_spoken(view: str) -> str:
    if view.startswith(GROUP_VIEW_PREFIX):
        return f"group {view[len(GROUP_VIEW_PREFIX):]}"
    return VIEW_SPOKEN.get(view, VIEW_SPOKEN[VIEW_ALL])


def in_view(info: SessionInfo, view: str) -> bool:
    """Whether the list shows ``info`` in ``view``. Archived sessions are only
    in the Archived view (and in a group they were put in)."""
    if view.startswith(GROUP_VIEW_PREFIX):
        return view[len(GROUP_VIEW_PREFIX):] in info.groups
    if view == VIEW_ARCHIVED:
        return info.archived
    if info.archived:
        return False
    if view == VIEW_ACTIVE:
        return info.state in (NEEDS_YOU, WORKING)
    if view == VIEW_NEEDS_YOU:
        return info.state == NEEDS_YOU
    if view == VIEW_DESKTOP:
        return not info.is_own
    if view == VIEW_OWN:
        return info.is_own
    if view == VIEW_REMOTE:
        return info.remote
    return True


def sort_sessions(sessions: Iterable[SessionInfo],
                  order: str = SORT_STATUS) -> List[SessionInfo]:
    """The list in ``order`` (one of SORT_VALUES; anything else is by status).

    By status: needs you first, then working, then the rest; newest first in
    each. Title and folder compare without regard to case.
    """
    def newest(s: SessionInfo) -> int:
        return -(s.last_activity_ms or 0)

    if order == SORT_NEWEST:
        key = lambda s: (newest(s), s.key)  # noqa: E731
    elif order == SORT_OLDEST:
        key = lambda s: (-newest(s), s.key)  # noqa: E731
    elif order == SORT_TITLE:
        key = lambda s: ((s.title or "").casefold(), newest(s), s.key)  # noqa: E731
    elif order == SORT_FOLDER:
        key = lambda s: (s.repo.casefold(), newest(s), s.key)  # noqa: E731
    else:
        key = lambda s: (_STATE_ORDER.get(s.state, 3), newest(s), s.key)  # noqa: E731
    return sorted(sessions, key=key)


# ---------------------------------------------------------------------------
# Live state (~/.claude/sessions/<pid>.json)
# ---------------------------------------------------------------------------


@dataclass
class LiveStatus:
    status: str          # "busy" | "idle" | other
    pid: int
    updated_ms: int = 0


def load_live_status(directory: Optional[Path] = None,
                     alive=platform_paths.pid_alive,
                     started=platform_paths.process_start) -> Dict[str, LiveStatus]:
    """Map of session id (both the cli id and the desktop local_ id) -> status.

    A pid file whose process has exited is stale and ignored, and so is one
    whose pid Windows has since given to another process (#5): its
    ``procStart`` doesn't match when the running process started.
    """
    directory = directory or platform_paths.live_sessions_dir()
    result: Dict[str, LiveStatus] = {}
    try:
        files = list(directory.glob("*.json"))
    except OSError:
        return result
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        pid = data.get("pid")
        if not isinstance(pid, int):
            try:
                pid = int(path.stem)
            except ValueError:
                continue
        if not alive(pid):
            continue
        if not _same_process(data.get("procStart"), started(pid)):
            continue
        status = LiveStatus(status=str(data.get("status") or ""), pid=pid,
                            updated_ms=_int(data.get("statusUpdatedAt") or data.get("updatedAt")))
        for id_field in ("sessionId", "hostSessionId"):
            value = data.get(id_field)
            if isinstance(value, str) and value:
                result[value] = status
    return result


def _same_process(recorded, actual: Optional[int]) -> bool:
    """Whether the pid file's ``procStart`` is the running process's start.
    True when either isn't known: then the pid is all there is to go on. A
    process that isn't yours can't be the Claude Code that wrote the file."""
    try:
        recorded = int(float(str(recorded)))
    except (TypeError, ValueError, OverflowError):
        return True
    if actual is None:
        return True
    if actual == platform_paths.NOT_YOURS:
        return False
    # The same clock read twice can differ in the last digits: a second apart
    # is still the same process; a reused pid started long after.
    return abs(recorded - actual) < 10_000_000


# ---------------------------------------------------------------------------
# Desktop app metadata
# ---------------------------------------------------------------------------


@dataclass
class DesktopLoadResult:
    sessions: List[SessionInfo] = field(default_factory=list)
    unreadable_files: int = 0
    #: Every cli session id the desktop app owns, archived ones included.
    #: Used by the --resume guard.
    desktop_cli_ids: Set[str] = field(default_factory=set)


def load_desktop_sessions(directory: Optional[Path] = None,
                          live: Optional[Dict[str, LiveStatus]] = None,
                          include_archived: bool = False) -> DesktopLoadResult:
    """The desktop app's sessions. Archived ones are left out unless
    ``include_archived`` (the list's Archived view, #32); they come with
    ``archived`` set."""
    directories = [directory] if directory else platform_paths.desktop_sessions_dirs()
    live = live if live is not None else {}
    result = DesktopLoadResult()
    # A session in two folders (both kinds of desktop app install, #183) is
    # read once, from the copy written last.
    newest: Dict[str, Path] = {}
    for folder in directories:
        try:
            found = list(folder.glob("**/local_*.json"))
        except OSError:
            continue
        for path in found:
            known = newest.get(path.name)
            if known is None or _mtime(path) > _mtime(known):
                newest[path.name] = path
    for path in newest.values():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            result.unreadable_files += 1
            continue
        if not isinstance(data, dict):
            result.unreadable_files += 1
            continue
        cli_id = data.get("cliSessionId")
        if isinstance(cli_id, str) and cli_id:
            result.desktop_cli_ids.add(cli_id)
        if data.get("isArchived") and not include_archived:
            continue
        info = desktop_session_from_metadata(data, live)
        if info is not None:
            result.sessions.append(info)
    return result


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def desktop_session_from_metadata(data: dict,
                                  live: Dict[str, LiveStatus]) -> Optional[SessionInfo]:
    local_id = data.get("sessionId")
    if not isinstance(local_id, str) or not platform_paths.is_safe_id(local_id):
        return None
    cli_id = data.get("cliSessionId")
    cli_id = cli_id if isinstance(cli_id, str) and platform_paths.is_safe_id(cli_id) else ""
    info = SessionInfo(
        source=DESKTOP,
        key=local_id,
        title=str(data.get("title") or "").strip() or "Untitled session",
        cwd=str(data.get("cwd") or ""),
        cli_session_id=cli_id,
        desktop_session_id=local_id,
        last_activity_ms=_int(data.get("lastActivityAt") or data.get("createdAt")),
        permission_mode=str(data.get("permissionMode") or ""),
        archived=bool(data.get("isArchived")),
        remote=isinstance(data.get("bridgeSessionIds"), list) and bool(data["bridgeSessionIds"]),
    )
    info.state, info.detail = desktop_state(data, live.get(cli_id) or live.get(local_id))
    return info


def desktop_state(data: dict, live: Optional[LiveStatus]) -> "tuple[str, str]":
    """(state, detail) for a desktop session. Best effort by design."""
    if live is not None and live.status == "busy":
        return WORKING, ""
    summary = data.get("postTurnSummary")
    if isinstance(summary, dict) and _summary_is_current(data, summary):
        needs = str(summary.get("needs_action") or "").strip()
        category = str(summary.get("status_category") or "").strip().lower()
        if needs:
            return NEEDS_YOU, needs
        if category in _NEEDS_YOU_CATEGORIES:
            detail = (str(summary.get("status_detail") or "").strip()
                      or category.replace("_", " "))
            return NEEDS_YOU, detail
    return IDLE, ""


def _summary_is_current(data: dict, summary: dict) -> bool:
    """A summary of an older turn says nothing about the latest one."""
    last = data.get("lastAssistantUuid")
    summarized = summary.get("summarizes_uuid") or data.get("postTurnSummaryFor")
    if isinstance(last, str) and last and isinstance(summarized, str) and summarized:
        return last == summarized
    return True


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
