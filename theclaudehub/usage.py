"""How full a session's context is, and how much of the plan's usage is
left (#19), as words.

Context comes from the token counts in Claude's latest reply (transcript, or
the turn's own result). The window is what Claude Code reported for the
model when a turn of ours said so; otherwise 200,000, or 1,000,000 once a
session has gone past 200,000 (some models and plans have the larger
window, and a session can't use more than it has).

Usage limits come from the ``rate_limit_event`` a turn reports, e.g.
``{"status": "allowed", "rateLimitType": "five_hour", "resetsAt": 1791338400,
"unifiedWindows": {"five_hour": {"utilization": 0.08, "resetsAt": ...},
"seven_day": {"utilization": 0.34, "resetsAt": ...}}}``. Seen with Claude Code
2.1.286; read defensively.
"""
from __future__ import annotations

import re
import time
from typing import Optional

STANDARD_WINDOW = 200_000
LARGE_WINDOW = 1_000_000
#: Said once per session when the context passes this share.
CONTEXT_WARNING = 0.8
#: Said once per limit window when usage passes this share.
LIMIT_WARNING = 0.9

_WINDOW_NAMES = {"five_hour": "5-hour limit", "seven_day": "weekly limit",
                 "seven_day_opus": "weekly Opus limit", "seven_day_sonnet": "weekly Sonnet limit"}
_LIMIT_REACHED = re.compile(r"usage limit reached\|(\d{9,})", re.IGNORECASE)


def context_window(model: str = "", tokens: int = 0, reported: int = 0) -> int:
    if reported and reported >= tokens:
        return reported
    if "[1m]" in (model or "") or tokens > STANDARD_WINDOW:
        return LARGE_WINDOW
    return STANDARD_WINDOW


def context_share(tokens: int, window: int) -> float:
    return min(tokens / window, 1.0) if window and tokens else 0.0


def context_text(tokens: int, window: int) -> str:
    """"Context 62% full: 124,000 of 200,000 tokens." """
    if not tokens:
        return "Context: not known until Claude's next reply."
    share = context_share(tokens, window)
    return f"Context {round(share * 100)}% full: {tokens:,} of {window:,} tokens."


def when(epoch: float, now: Optional[float] = None) -> str:
    """"at 7:00 AM" today, "tomorrow at 7:00 AM", "on Friday at 3:00 PM"."""
    moment = time.localtime(epoch)
    today = time.localtime(now if now is not None else time.time())
    clock = time.strftime("%I:%M %p", moment).lstrip("0")
    days = (time.mktime((moment.tm_year, moment.tm_mon, moment.tm_mday, 0, 0, 0, 0, 0, -1))
            - time.mktime((today.tm_year, today.tm_mon, today.tm_mday, 0, 0, 0, 0, 0, -1))) / 86400
    if round(days) <= 0:
        return f"at {clock}"
    if round(days) == 1:
        return f"tomorrow at {clock}"
    if days < 7:
        return f"on {time.strftime('%A', moment)} at {clock}"
    return f"on {time.strftime('%d %B', moment).lstrip('0')} at {clock}"


def _windows(info: dict):
    """(name, utilization 0-1, resets epoch or 0) for each window reported."""
    windows = info.get("unifiedWindows") if isinstance(info, dict) else None
    found = []
    if isinstance(windows, dict):
        for key, window in windows.items():
            if isinstance(window, dict) and isinstance(window.get("utilization"), (int, float)):
                found.append((_WINDOW_NAMES.get(key, key.replace("_", " ") + " limit"),
                              float(window["utilization"]), float(window.get("resetsAt") or 0)))
    return found


def limits_text(info: Optional[dict], now: Optional[float] = None) -> str:
    """"5-hour limit 8% used, resets at 7:00 AM. Weekly limit 34% used,
    resets on Friday at 3:00 PM." """
    if not isinstance(info, dict) or not info:
        return "Usage limits: not known until a TheClaudeHub session runs a turn."
    parts = []
    for name, used, resets in _windows(info):
        part = f"{name[0].upper()}{name[1:]} {round(used * 100)}% used"
        if resets:
            part += f", resets {when(resets, now)}"
        parts.append(part + ".")
    if info.get("status") not in (None, "allowed", "allowed_warning"):
        reset = info.get("resetsAt")
        parts.insert(0, "You've reached a usage limit" + (
            f"; it resets {when(float(reset), now)}." if reset else "."))
    if info.get("isUsingOverage"):
        parts.append("Turns are now billed as extra usage.")
    return " ".join(parts) or "Usage limits: Claude Code didn't say."


def limit_warning(info: Optional[dict], now: Optional[float] = None) -> Optional[str]:
    """Something worth saying unasked: a limit reached, or nearly."""
    if not isinstance(info, dict):
        return None
    if info.get("status") not in (None, "allowed", "allowed_warning"):
        return limits_text(info, now)
    for name, used, resets in _windows(info):
        if used >= LIMIT_WARNING:
            reset = f"; it resets {when(resets, now)}" if resets else ""
            return f"You've used {round(used * 100)}% of your {name}{reset}."
    return None


def limit_warning_key(info: Optional[dict]) -> Optional[str]:
    """Which warning ``limit_warning`` would give, as a key that stays the same
    while the percentage creeps up: said once per limit window."""
    if not isinstance(info, dict):
        return None
    if info.get("status") not in (None, "allowed", "allowed_warning"):
        return f"reached:{info.get('resetsAt')}"
    for name, used, resets in _windows(info):
        if used >= LIMIT_WARNING:
            return f"{name}:{int(resets)}"
    return None


def friendly_error(text: str, now: Optional[float] = None) -> str:
    """A turn's error in plain words where it's a usage limit
    ("Claude AI usage limit reached|1791338400")."""
    match = _LIMIT_REACHED.search(text or "")
    if match:
        return (f"You've reached your Claude usage limit. It resets "
                f"{when(int(match.group(1)), now)}.")
    return text
