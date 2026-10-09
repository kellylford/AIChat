"""A made-up world for the window to run in: every path, the clipboard,
speech, sign-in, notifications and the web view replaced, so nothing touches
the real %APPDATA%, the real claude, the desktop app's files or the speakers.

Shared by the hidden-window tests (``test_ui_hidden.py``'s ``env`` fixture)
and the visual probe (``tools/ui_probe.py``, #155), so what the probe shows
is the window the tests check. ``setattr`` is pytest's
``monkeypatch.setattr`` in the tests, and a plain patcher in the probe.
"""
import json
import time
from pathlib import Path

import wx

from thechatplace import platform_paths, speech

from records import lines

FAKE_COMMANDS = [
    {"name": "blog-publish", "description": "Publish a post to the blog", "argumentHint": ""},
    {"name": "compact", "description": "Clear history but keep a summary", "builtin": True,
     "argumentHint": "<optional instructions>"},
    {"name": "context", "description": "Show what's using the context", "builtin": True},
]


def now_ms():
    return int(time.time() * 1000)


def install(root: Path, setattr, formatted_view: bool = False) -> dict:
    """Point the app at folders under ``root`` and replace everything that
    would reach outside it. ``formatted_view`` leaves the real web view in
    (the probe photographs it); the tests keep it out, because it opens
    modal and waits."""
    desktop = root / "desktop"
    live = root / "live"
    projects = root / "projects"
    cowork = root / "cowork"
    for folder in (desktop, live, projects, cowork):
        folder.mkdir(parents=True, exist_ok=True)
    setattr(platform_paths, "desktop_sessions_dirs", lambda: [desktop])
    setattr(platform_paths, "cowork_sessions_dirs", lambda: [cowork])
    setattr(platform_paths, "live_sessions_dir", lambda: live)
    setattr(platform_paths, "projects_dir", lambda: projects)
    setattr(speech, "DEFAULT_SETTINGS_PATH", root / "speech.json")
    # The Chat Place's own files (groups.json) go here, never in the real %APPDATA%.
    setattr(platform_paths, "app_data_dir", lambda: root / "appdata")
    # No real claude --version (bug reports) or clipboard.
    from thechatplace import bugreport
    from thechatplace.ui import dialogs, main_frame
    setattr(bugreport, "claude_code_version", lambda: "2.1.286 (Claude Code)")
    copied = []
    setattr(main_frame.MainFrame, "_copy_text",
            lambda self, text: copied.append(text) or True)
    # Nor the real claude for its sign-in (#52): signed in, unless a test says not.
    from thechatplace import signin
    setattr(signin, "check", lambda *a, **k: signin.SignIn(
        True, signed_in=True, method="claude.ai", plan="max", email="k@example.com"))
    # Nor the real claude for a folder's slash commands (#23).
    setattr(main_frame, "fetch_commands", lambda exe, cwd: list(FAKE_COMMANDS))
    spoken = []
    feedback = []

    def speak(text, settings, interrupt=True):
        (spoken if interrupt else feedback).append(text)
    setattr(speech.speaker, "speak", speak)
    # The frame points the shared speaker at itself (#98); put it back after,
    # so no later test reaches a destroyed frame through it.
    setattr(speech.speaker, "on_problem", None)
    setattr(speech.speaker, "last_problem", "")
    setattr(main_frame, "list_speech_options", lambda: speech.default_options())
    if not formatted_view:
        # No real web page: it would open modal and wait. Tests that want the
        # formatted view put a fake in.
        setattr(main_frame, "formatted_view_available", lambda: False)
        setattr(dialogs, "formatted_view_available", lambda: False)
    opened = []
    setattr(platform_paths, "open_url", lambda url: opened.append(url))
    # Nor real Claude Code files, an editor or Explorer (#92).
    setattr(platform_paths, "claude_home", lambda: root / "claude")
    setattr(platform_paths, "edit_file", lambda path: opened.append(("edit", path)))
    setattr(platform_paths, "show_in_folder", lambda path: opened.append(("show", path)))
    boxes = []
    setattr(wx, "MessageBox", lambda *a, **k: boxes.append(a[0]) or wx.YES)
    # No real Windows notifications (#20): they're recorded. The hidden test
    # window is never the active one, so every notification would show.
    notified = []

    class FakeNotifier:
        def __init__(self, on_click, tooltip):
            self.on_click = on_click

        def show(self, title, message, key):
            notified.append((title, message, key))
            return True

        def close(self):
            pass
    setattr(main_frame, "Notifier", FakeNotifier)
    # Nor take the Mac's menu bar from the app you're using.
    activated = []
    from thechatplace.ui import mac_a11y
    setattr(mac_a11y, "activate_app", lambda: activated.append(True) or True)
    return {"desktop": desktop, "cowork": cowork, "projects": projects, "spoken": spoken,
            "copied": copied, "feedback": feedback, "opened": opened, "boxes": boxes, "tmp": root,
            "live": live, "notified": notified, "activated": activated}


def add_desktop(env, local, cli, title, cwd="C:\\G\\Repo", ago=60_000, **extra):
    folder = env["desktop"] / local / "org"
    folder.mkdir(parents=True, exist_ok=True)
    data = {"sessionId": local, "cliSessionId": cli, "cwd": cwd, "title": title,
            "isArchived": False, "lastActivityAt": now_ms() - ago}
    data.update(extra)
    (folder / f"{local}.json").write_text(json.dumps(data), encoding="utf-8")


def add_transcript(env, cwd, cli, records):
    folder = env["projects"] / platform_paths.encode_cwd(cwd)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{cli}.jsonl"
    path.write_text("\n".join(lines(*records)) + "\n", encoding="utf-8")
    return path


def pump(condition, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        wx.GetApp().ProcessPendingEvents()
        wx.YieldIfNeeded()
        if condition():
            return True
        time.sleep(0.02)
    return False
