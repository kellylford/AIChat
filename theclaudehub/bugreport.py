"""Reporting a bug from inside the app (#28), modelled on QuickMail's.

The report is what you type (a summary, what happened, what you expected,
steps) plus a snapshot of non-sensitive facts about the app: versions, the
speech route and announcement level, which view and sort the list uses, and
how many sessions of each kind it lists. Never a session's title, folder,
message text, or anything that names a person or path: the report becomes a
public issue.

QuickMail sends reports through a small relay (a Cloudflare Worker holding a
GitHub App key), so nobody needs a GitHub account. TheClaudeHub has no relay
yet: the dialog opens a GitHub "new issue" page with the report filled in,
and copies the full report to the clipboard in case the page is cut short.
When a relay exists, ``RELAY_URL`` and ``RELAY_KEY`` are the only change.
"""
from __future__ import annotations

import platform
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import __version__, platform_paths

#: Where issues are filed. One place to change when the app is renamed.
REPO = "kellylford/AIChat"
#: A bug-report relay, as QuickMail has; empty until one is set up.
RELAY_URL = ""
RELAY_KEY = ""
#: Browsers and the shell cut very long URLs; the clipboard has it all.
MAX_URL_BODY = 4000


@dataclass
class BugReport:
    summary: str
    what_happened: str
    expected: str = ""
    steps: str = ""
    #: (label, value) facts about the app, from ``environment``.
    environment: List[tuple] = field(default_factory=list)


def claude_code_version() -> str:
    """"2.1.286 (Claude Code)", or why it isn't known. Quick, hidden."""
    path = platform_paths.claude_executable()
    if not path:
        return "not found"
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=8,
                             creationflags=platform_paths.hidden_window_flags())
        return (out.stdout or out.stderr).strip().splitlines()[0][:80] or "unknown"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


def environment(speech, counts: Dict[str, int], claude_version: Optional[str] = None) -> List[tuple]:
    """Facts for the report. ``speech`` is the SpeechSettings; ``counts`` how
    many sessions of each kind are listed. No names, titles or paths."""
    try:
        import wx
        wx_version = wx.version()
    except Exception:  # noqa: BLE001
        wx_version = "not loaded"
    frozen = bool(getattr(sys, "frozen", False))
    facts = [
        ("TheClaudeHub", f"{__version__} ({'installed build' if frozen else 'run from source'})"),
        ("Windows", platform.platform()),
        ("Python", platform.python_version()),
        ("wxPython", wx_version),
        ("Claude Code", claude_version if claude_version is not None else claude_code_version()),
        ("Announcements", f"{speech.announce}, speech engine {speech.engine}"),
        ("Session list", f"showing {speech.session_view}, sorted {speech.session_order}"),
        ("Reading", "formatted full messages" if speech.formatted_messages else "plain text",),
    ]
    if counts:
        facts.append(("Sessions listed", ", ".join(f"{n} {kind}" for kind, n in counts.items())))
    return facts


def report_text(report: BugReport) -> str:
    """The issue body, in Markdown."""
    parts = ["### What happened", report.what_happened.strip() or "(not given)", ""]
    if report.expected.strip():
        parts += ["### What I expected", report.expected.strip(), ""]
    if report.steps.strip():
        parts += ["### Steps to reproduce", report.steps.strip(), ""]
    if report.environment:
        parts += ["### Environment"] + [f"- {label}: {value}" for label, value in report.environment]
        parts.append("")
    parts.append("_Reported from TheClaudeHub's Help, Report a Bug._")
    return "\n".join(parts)


def new_issue_url(report: BugReport) -> str:
    """A GitHub "new issue" page with the report filled in (cut to fit a
    URL; the clipboard holds all of it)."""
    body = report_text(report)
    if len(body) > MAX_URL_BODY:
        body = body[:MAX_URL_BODY] + ("\n\n…(cut short here: the whole report is on your "
                                      "clipboard; paste it over this)")
    query = urllib.parse.urlencode({"title": report.summary.strip(), "body": body,
                                    "labels": "bug"})
    return f"https://github.com/{REPO}/issues/new?{query}"
