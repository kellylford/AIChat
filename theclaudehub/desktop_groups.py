"""The Claude desktop app's own groups of Code sessions (#51), read-only.

The desktop app keeps them in ``claude_desktop_config.json``, beside its
``claude-code-sessions`` folder, under
``preferences.epitaxyPrefs["dframe-group-scopes"]``: one entry per
``<account>/<organisation>``, each with

- ``groups``: ``[{"id": "cg-…", "name": "IDT"}, …]``, in the app's order;
- ``assignments``: ``{"code:local_<id>": "cg-…"}``, a session's one group.

TheClaudeHub only reads this: the desktop app owns the file and rewrites it,
so its groups are changed in the desktop app. Anything unexpected (no file,
another shape after an update) just means no desktop groups.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

CONFIG_NAME = "claude_desktop_config.json"
_SESSION_PREFIX = "code:"


@dataclass
class DesktopGroups:
    #: Group names, in the desktop app's order, each once.
    names: List[str] = field(default_factory=list)
    #: Session key ("local_…") -> its group's name.
    by_session: Dict[str, str] = field(default_factory=dict)


def load_desktop_groups(session_dirs: Iterable[Path]) -> DesktopGroups:
    """The groups from the config beside each desktop sessions folder."""
    result = DesktopGroups()
    for folder in session_dirs:
        try:
            raw = json.loads((Path(folder).parent / CONFIG_NAME).read_text(encoding="utf-8"))
            scopes = raw["preferences"]["epitaxyPrefs"]["dframe-group-scopes"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(scopes, dict):
            continue
        for scope in scopes.values():
            _read_scope(scope, result)
    return result


def _read_scope(scope, result: DesktopGroups) -> None:
    if not isinstance(scope, dict):
        return
    names: Dict[str, str] = {}
    for group in scope.get("groups") or []:
        if isinstance(group, dict) and isinstance(group.get("id"), str):
            name = str(group.get("name") or "").strip()
            if name:
                names[group["id"]] = name
                if name not in result.names:
                    result.names.append(name)
    assignments = scope.get("assignments")
    if not isinstance(assignments, dict):
        return
    for session, group_id in assignments.items():
        if (isinstance(session, str) and session.startswith(_SESSION_PREFIX)
                and group_id in names):
            result.by_session[session[len(_SESSION_PREFIX):]] = names[group_id]
