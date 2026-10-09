"""The visual probe (#155): open each of The Chat Place's screens on made-up
data, and save a picture of it and a JSON description of its controls.

    python tools/ui_probe.py --out probe-run [--tag light-100] [--surface main-own ...]
    python tools/ui_probe.py --list

It shows real windows, so on Windows run it in the test VM (``tools/ui_probe_vm.ps1``
does that, for every variant in ``tools/ui_probe_plan.json``), never on a PC
someone is using with a screen reader. The data is the hidden-window tests'
(``tests/fake_env.py``): no real sessions, %APPDATA%, claude, speech or web.

Each surface is opened the way a person opens it, through the frame's own
menu handler, wherever made-up data can get it there. A modal dialog is
caught by a timer while it is open, photographed, then cancelled.

The JSON beside each picture lists every control with its class, label,
rectangle and best size, and flags text that doesn't fit and controls
outside the window. ``tests/test_ui_probe.py`` checks the surfaces still
cover every dialog, so a new dialog can't go unphotographed.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import wx  # noqa: E402

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

#: How long a dialog must stay open before it's photographed, so its first
#: paint (and a list's first selection) has happened.
SETTLE_SECONDS = 0.8
#: The formatted view draws in another process; it gets longer.
WEBVIEW_SETTLE_SECONDS = 2.5
DIALOG_TIMEOUT_SECONDS = 20.0


# -- capture ------------------------------------------------------------------------------


def _extended_frame_bounds(hwnd):
    """The window's visible rectangle on screen: GetWindowRect includes
    Windows 10/11's invisible resize border, which would show as a margin."""
    rect = (ctypes.c_long * 4)()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect),
            ctypes.sizeof(rect)) != 0:
        return None
    return tuple(rect)


def _window_rect(hwnd):
    rect = (ctypes.c_long * 4)()
    ctypes.windll.user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    return tuple(rect)


def _one_colour(bitmap: wx.Bitmap) -> bool:
    """True if a grid of samples across the picture are all the same colour:
    what PrintWindow returns when it couldn't draw the window."""
    image = bitmap.ConvertToImage()
    w, h = image.GetWidth(), image.GetHeight()
    if w < 2 or h < 2:
        return True
    seen = set()
    for y in range(1, h, max(1, h // 12)):
        for x in range(1, w, max(1, w // 12)):
            seen.add((image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y)))
            if len(seen) > 1:
                return False
    return True


def _capture_windows(window: wx.TopLevelWindow) -> tuple[wx.Bitmap, str]:
    """PrintWindow with PW_RENDERFULLCONTENT, which includes the formatted
    view's WebView2 (drawn by another process); a screen copy if that came
    back blank. Cropped to the visible frame."""
    hwnd = window.GetHandle()
    left, top, right, bottom = _window_rect(hwnd)
    width, height = right - left, bottom - top
    bitmap = wx.Bitmap(width, height)
    dc = wx.MemoryDC(bitmap)
    PW_RENDERFULLCONTENT = 2
    ok = ctypes.windll.user32.PrintWindow(ctypes.c_void_p(hwnd), ctypes.c_void_p(dc.GetHDC()),
                                          PW_RENDERFULLCONTENT)
    dc.SelectObject(wx.NullBitmap)
    method = "PrintWindow"
    if not ok or _one_colour(bitmap):
        window.Raise()
        wx.SafeYield()
        time.sleep(0.3)
        bitmap = wx.Bitmap(width, height)
        screen = wx.ScreenDC()
        dc = wx.MemoryDC(bitmap)
        dc.Blit(0, 0, width, height, screen, left, top)
        dc.SelectObject(wx.NullBitmap)
        method = "screen copy"
    bounds = _extended_frame_bounds(hwnd)
    if bounds:
        bl, bt, br, bb = bounds
        crop = wx.Rect(bl - left, bt - top, br - bl, bb - bt)
        if crop.width > 0 and crop.height > 0 and wx.Rect(0, 0, width, height).Contains(crop):
            bitmap = bitmap.GetSubBitmap(crop)
    return bitmap, method


def _mac_window_number(window) -> int:
    """The window's number for ``screencapture -l``: [[view window] windowNumber]."""
    objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    send = objc.objc_msgSend
    send.restype = ctypes.c_void_p
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    view = ctypes.c_void_p(window.GetHandle())
    nswindow = send(view, objc.sel_registerName(b"window"))
    send.restype = ctypes.c_long
    return int(send(ctypes.c_void_p(nswindow), objc.sel_registerName(b"windowNumber")))


def _capture_mac(window, path: Path) -> str:
    """``screencapture -l``: the window alone, without its shadow. Needs
    Screen Recording permission for the terminal running the probe."""
    number = _mac_window_number(window)
    subprocess.run(["screencapture", "-x", "-o", "-l", str(number), str(path)], check=True)
    return "screencapture"


def _capture_screen(window) -> tuple[wx.Bitmap, str]:
    rect = window.GetScreenRect()
    bitmap = wx.Bitmap(rect.width, rect.height)
    dc = wx.MemoryDC(bitmap)
    dc.Blit(0, 0, rect.width, rect.height, wx.ScreenDC(), rect.x, rect.y)
    dc.SelectObject(wx.NullBitmap)
    return bitmap, "screen copy"


def capture(window: wx.TopLevelWindow, path: Path) -> str:
    """Save a PNG of ``window`` to ``path``; returns how it was taken."""
    window.Update()
    wx.SafeYield()
    if IS_MAC:
        return _capture_mac(window, path)
    bitmap, method = _capture_windows(window) if IS_WINDOWS else _capture_screen(window)
    if not bitmap.SaveFile(str(path), wx.BITMAP_TYPE_PNG):
        raise RuntimeError(f"couldn't save {path}")
    return method


# -- describing the controls -------------------------------------------------------------

#: Controls whose text is drawn at its natural size: one smaller than its
#: best size is cutting text off.
_TEXT_CONTROLS = (wx.StaticText, wx.Button, wx.CheckBox, wx.RadioButton, wx.StaticBox)


def _label(control) -> str:
    try:
        return control.GetLabel()
    except Exception:  # noqa: BLE001
        return ""


def describe(window: wx.TopLevelWindow) -> dict:
    """Every shown control under ``window``: class, name, label, rectangle
    (in the window's client coordinates), best size, and what looks wrong.
    Plain data, for the review and for comparing two runs."""
    origin = window.ClientToScreen(wx.Point(0, 0))
    client = window.GetClientSize()
    controls = []

    def walk(parent, depth):
        for child in parent.GetChildren():
            if isinstance(child, wx.TopLevelWindow) or not child.IsShown():
                continue
            screen = child.GetScreenRect()
            rect = [screen.x - origin.x, screen.y - origin.y, screen.width, screen.height]
            best = child.GetBestSize()
            entry = {"class": type(child).__name__, "name": child.GetName(),
                     "label": _label(child), "rect": rect, "best": [best.width, best.height],
                     "depth": depth, "enabled": child.IsEnabled(), "problems": []}
            if isinstance(child, _TEXT_CONTROLS) and entry["label"]:
                if best.width > screen.width + 1 or best.height > screen.height + 1:
                    entry["problems"].append("text cut off: smaller than its best size")
            if isinstance(child, wx.ListBox):
                entry["items"] = [child.GetString(i) for i in range(min(child.GetCount(), 12))]
                entry["selection"] = child.GetSelection()
            elif isinstance(child, wx.TextCtrl):
                entry["value"] = child.GetValue()[:400]
            elif isinstance(child, wx.Choice):
                entry["value"] = child.GetStringSelection()
            # The status bar sits below the client area by design.
            if depth == 0 and not isinstance(child, wx.StatusBar):
                right, bottom = rect[0] + rect[2], rect[1] + rect[3]
                if (rect[0] < 0 or rect[1] < 0
                        or right > client.width + 1 or bottom > client.height + 1):
                    entry["problems"].append("outside the window")
            controls.append(entry)
            walk(child, depth + 1)
    walk(window, 0)
    _flag_overlaps(window, controls)
    return {"title": window.GetTitle(), "class": type(window).__name__,
            "size": list(window.GetSize()), "client": [client.width, client.height],
            "dpi": list(window.GetDPI()), "content_scale": window.GetContentScaleFactor(),
            "controls": controls}


def _flag_overlaps(window, controls):
    """Siblings (same parent, so the same depth and a shared container) whose
    rectangles cross. A group box's rectangle holds its options on purpose
    (#121), so a StaticBox is never counted."""
    by_depth = {}
    for entry in controls:
        if entry["class"] in ("StaticBox", "Panel", "ScrolledWindow"):
            continue
        by_depth.setdefault(entry["depth"], []).append(entry)
    for group in by_depth.values():
        for i, a in enumerate(group):
            ra = wx.Rect(*a["rect"])
            for b in group[i + 1:]:
                rb = wx.Rect(*b["rect"])
                if ra.width and ra.height and rb.width and rb.height and ra.Intersects(rb):
                    overlap = ra.Intersect(rb)
                    if overlap.width > 2 and overlap.height > 2:
                        a["problems"].append(f"overlaps {b['class']} {b['label'] or b['name']!r}")


# -- the made-up world ---------------------------------------------------------------------


class _Patch:
    """monkeypatch.setattr for a process that exits when it's done."""
    def __call__(self, target, name, value):
        setattr(target, name, value)


def _cwd(*parts):
    if IS_WINDOWS:
        return "C:\\Users\\probe\\Projects\\" + "\\".join(parts)
    return "/Users/probe/Projects/" + "/".join(parts)


FENCE = "`" * 3
LONG_MESSAGE = f"""## What changed

The upload test failed one run in ten because it read the progress file before the
writer had flushed it. It now waits for the writer to say it's done.

- `uploader.py`: flush and close before signalling
- `test_upload.py`: wait on the signal, not on a sleep

{FENCE}python
def finish(self):
    self._file.flush()
    self._file.close()
    self.done.set()
{FENCE}

| File | Lines added | Lines removed |
|---|---|---|
| uploader.py | 4 | 1 |
| test_upload.py | 6 | 3 |

See [the issue](https://github.com/example/repo/issues/42) for the history. A long line
follows so wrapping shows: {"wrapping " * 30}
"""


def build_world(root: Path, empty: bool = False) -> dict:
    """Install the fakes under ``root`` and write the probe's sessions."""
    import fake_env
    from records import assistant_block, text_block, tool_result, tool_use_block, user_text
    from thechatplace.ui import main_frame
    from thechatplace import platform_paths

    env = fake_env.install(root, _Patch(), formatted_view=True)

    class ProbeRunner:
        """A turn that never ends, so the window shows one in progress."""
        def __init__(self, command, cwd, prompt, on_event, images=None, remote_control=None):
            self.on_event = on_event
            self.session_started = True
            self.last_activity = "running a command"

        def start(self):
            pass

        def elapsed(self):
            return 75.0

        def cancel(self):
            pass

        def respond(self, request_id, response):
            return True

        def send_now(self, prompt):
            return True
    main_frame.TurnRunner = ProbeRunner
    platform_paths.find_claude = lambda: platform_paths.ClaudeLookup("claude.exe")
    env["runner"] = ProbeRunner
    if empty:
        return env

    repo = _cwd("AIChat")
    fake_env.add_desktop(env, "local_a", "cli-a", "Fix the flaky upload test", cwd=repo,
                         postTurnSummary={"status_category": "blocked",
                                          "needs_action": "Pick a name for the release branch"})
    fake_env.add_desktop(env, "local_b", "cli-b", "Write the release notes for 0.2",
                         cwd=_cwd("AIChat"), ago=3_600_000)
    fake_env.add_desktop(env, "local_c", "cli-c",
                         "A session whose title goes on and on to show what a very long title "
                         "does to the session list and the heading above the messages",
                         cwd=_cwd("Website"), ago=86_400_000)
    fake_env.add_transcript(env, repo, "cli-a", [
        user_text("The upload test fails now and then. Can you find out why?"),
        assistant_block(text_block("I'll look at the test and the uploader."), "m1"),
        assistant_block(tool_use_block("Bash", {"command": "pytest tests/test_upload.py -q"},
                                       "t1"), "m2"),
        tool_result("t1", "1 failed, 11 passed"),
        assistant_block(text_block(LONG_MESSAGE), "m3"),
        user_text("Thanks. Which branch name should the release use?")])
    own_cwd = _cwd("Scratch")
    edit_path = os.path.join(own_cwd, "uploader.py")
    fake_env.add_transcript(env, own_cwd, "own-1", [
        user_text("Make the uploader flush before it signals."),
        assistant_block(tool_use_block("Edit", {"file_path": edit_path,
                                                "old_string": "self.done.set()",
                                                "new_string": "self._file.flush()\n"
                                                              "self._file.close()\n"
                                                              "self.done.set()"}, "e1"), "m1"),
        tool_result("e1", "The file has been updated.",
                    toolUseResult={"filePath": edit_path}),
        assistant_block(text_block(LONG_MESSAGE), "m2")])
    return env


def build_frame(env, empty: bool = False):
    import fake_env
    from thechatplace.own_store import OwnSession, OwnSessionStore
    from thechatplace.ui.main_frame import MainFrame
    store = OwnSessionStore(env["tmp"] / "own.json")
    if not empty:
        store.add(OwnSession("own-1", "Visual probe", _cwd("Scratch"),
                             last_activity_ms=fake_env.now_ms()))
    frame = MainFrame(store=store, check_updates_at_start=False)
    if not empty:
        fake_env.pump(lambda: frame.session_list.GetCount() == 4, timeout=15)
    return frame


# -- surfaces -------------------------------------------------------------------------------

def _select(frame, title):
    for i in range(frame.session_list.GetCount()):
        if frame.session_list.GetString(i).startswith(title) or title in frame.session_list.GetString(i):
            frame.session_list.SetSelection(i)
            return
    raise RuntimeError(f"{title} isn't in the session list")


def _open(frame, title, count=None):
    import fake_env
    _select(frame, title)
    frame.on_open_session()
    fake_env.pump(lambda: frame._chat_loaded and (count is None or frame.chat_list.GetCount() >= count),
                  timeout=10)


def _select_message(frame, needle):
    for i in range(frame.chat_list.GetCount()):
        if needle in frame.chat_list.GetString(i):
            frame.chat_list.SetSelection(i)
            return
    raise RuntimeError(f"no message containing {needle!r}")


def _reset(frame):
    """Back to the state each surface starts from: activity hidden, no turn."""
    if frame.activity_check.GetValue():
        frame.activity_check.SetValue(False)
        frame.on_toggle_activity_check(None)


def _pending(frame, request):
    """Claude waiting on ``request`` in the own session, as a turn reports it."""
    from thechatplace.claude_cli import TurnEvent
    _open(frame, "Visual probe")
    runner = frame._runners.get("own-1")
    if runner is None:
        frame._runners["own-1"] = runner = frame_runner(frame)
    frame._on_turn_event({"id": "own-1"}, "Visual probe",
                         TurnEvent("permission", text=request.summary(), request=request))


def frame_runner(frame):
    from thechatplace.ui import main_frame
    return main_frame.TurnRunner([], "", "", None)


def _request(tool, tool_input, request_id="r1"):
    from thechatplace.claude_cli import PermissionRequest
    return PermissionRequest(request_id, tool, tool_input, suggestions=[])


# Each surface: (what it shows, how to get there). A main-window surface's
# function sets the window up and returns None; a dialog surface's returns
# the call that opens it (a menu handler, usually), run while the probe
# waits to catch the dialog.

def s_main_start(frame, env):
    _reset(frame)


def s_main_own(frame, env):
    _reset(frame)
    _open(frame, "Visual probe")


def s_main_own_working(frame, env):
    _reset(frame)
    _open(frame, "Visual probe")
    frame.reply_text.SetValue("Now run the whole suite.")
    frame.on_send()
    frame.reply_text.SetValue("And then open a PR.")
    frame.on_send()
    frame.reply_text.SetValue("Draft of a message still being typed")


def s_main_desktop(frame, env):
    _reset(frame)
    _open(frame, "Fix the flaky upload test")


def s_main_activity(frame, env):
    _open(frame, "Fix the flaky upload test")
    frame.activity_check.SetValue(True)
    frame.on_toggle_activity_check(None)


def s_main_last_message(frame, env):
    from thechatplace.sessions import FIELD_LAST_MESSAGE
    _reset(frame)
    if FIELD_LAST_MESSAGE not in frame.speech.session_fields:
        frame.speech.session_fields = list(frame.speech.session_fields) + [FIELD_LAST_MESSAGE]
    frame.refresh_sessions(force=True)
    import fake_env
    fake_env.pump(lambda: not frame._snapshot_busy, timeout=10)
    time.sleep(0.5)
    fake_env.pump(lambda: True, timeout=0.5)


def s_main_update_ready(frame, env):
    _reset(frame)
    frame.status_parts.set("update", "Update 0.2.0 ready")
    frame.status_parts.layout()


def d_shortcuts_page(frame, env):
    return frame.on_shortcuts


def d_shortcuts_plain(frame, env):
    from thechatplace.ui.dialogs import ShortcutsDialog
    return lambda: frame._modal(ShortcutsDialog(frame))


def d_user_guide(frame, env):
    return frame.on_user_guide


def d_message_formatted(frame, env):
    _open(frame, "Fix the flaky upload test")
    _select_message(frame, "What changed")
    frame.speech.formatted_messages = True
    return frame.on_read_message


def d_message_plain(frame, env):
    _open(frame, "Fix the flaky upload test")
    _select_message(frame, "What changed")
    frame.speech.formatted_messages = False
    return frame.on_read_message


def d_settings(frame, env):
    return frame.on_settings


def d_new_session(frame, env):
    return frame.on_new_session


def d_continue_here(frame, env):
    _open(frame, "Fix the flaky upload test")
    return frame.on_continue_here


def d_update_installed(frame, env):
    from thechatplace.ui.dialogs import UpdateInstalledDialog
    return lambda: frame._modal(UpdateInstalledDialog(frame, "0.2.0", lambda: None))


def d_permission(frame, env):
    _pending(frame, _request("Bash", {"command": "git push origin release/0.2",
                                      "description": "Push the release branch"}))
    return frame.on_answer


def d_question(frame, env):
    _pending(frame, _request("AskUserQuestion", {"questions": [
        {"header": "Branch", "question": "Which name should the release branch use?",
         "options": [{"label": "release/0.2", "description": "Matches the last release"},
                     {"label": "v0.2-prep", "description": "Shorter"}]},
        {"header": "Checks", "question": "Which checks should run first?", "multiSelect": True,
         "options": [{"label": "Unit tests"}, {"label": "Smoke test"}, {"label": "Lint"}]}]},
        "q1"))
    return frame.on_answer


def d_plan(frame, env):
    _pending(frame, _request("ExitPlanMode", {"plan": (
        "# Plan\n\n1. Flush and close the progress file before signalling.\n"
        "2. Wait on the signal in the test.\n3. Run the suite ten times.\n")}, "p1"))
    return frame.on_answer


def d_manage_groups(frame, env):
    if "Releases" not in frame.groups.names():
        frame.groups.create("Releases")
        frame.groups.create("Website")
        for session in frame._snapshot.sessions[:2]:
            frame.groups.add("Releases", session.key)
    return frame.on_manage_groups


def d_command_picker(frame, env):
    import fake_env
    from thechatplace.ui.main_frame import _folder_key
    _open(frame, "Visual probe")
    key = _folder_key(frame._open.cwd)
    if key not in frame._commands:
        frame._fetch_commands(frame._open.cwd)
        fake_env.pump(lambda: key in frame._commands, timeout=10)
    return frame.on_insert_command


def d_bug_report(frame, env):
    return frame.on_report_bug


def d_code_blocks(frame, env):
    _open(frame, "Fix the flaky upload test")
    _select_message(frame, "What changed")
    return frame.on_code_blocks


def d_changes(frame, env):
    _open(frame, "Visual probe")
    return frame.on_changes


def d_usage(frame, env):
    _open(frame, "Visual probe")
    return frame.on_usage


def d_about_you(frame, env):
    home = env["tmp"] / "claude"
    (home / "skills" / "release").mkdir(parents=True, exist_ok=True)
    (home / "CLAUDE.md").write_text("# How I like to work\n\nTest everything.\n", encoding="utf-8")
    (home / "skills" / "release" / "SKILL.md").write_text(
        "---\nname: release\ndescription: Make a release\n---\nSteps.\n", encoding="utf-8")
    return frame.on_about_you


def d_session_columns(frame, env):
    return frame.on_session_columns


def d_prompts(frame, env):
    if not len(frame.prompts):
        frame.prompts.add("Review", "Review this change for bugs, then for accessibility.")
        frame.prompts.add("Release notes", "Draft release notes for what changed since the last tag.")
    return frame.on_prompts


def d_prompt_edit(frame, env):
    from thechatplace.ui.dialogs import PromptEditDialog
    return lambda: frame._modal(PromptEditDialog(frame, "Edit Prompt", "Review",
                                                 "Review this change for bugs."))


def d_rename(frame, env):
    _select(frame, "Visual probe")
    return frame.on_rename


def d_message_box(frame, env):
    """A plain wx.MessageBox, as the app shows for a warning."""
    real = getattr(wx, "_probe_real_message_box", None)
    return lambda: real("The Chat Place couldn't open that file.", "The Chat Place",
                        wx.OK | wx.ICON_WARNING, frame)


#: name -> (kind, function, what it shows). Order is the order photographed:
#: main-window states first, then dialogs.
SURFACES = {
    "main-start": ("window", s_main_start, "Main window as it opens: session list, no session loaded"),
    "main-own": ("window", s_main_own, "An own session loaded: messages and the reply box"),
    "main-own-working": ("window", s_main_own_working,
                         "An own session mid-turn, with messages queued"),
    "main-desktop": ("window", s_main_desktop,
                     "A desktop app session loaded: the read-only panel instead of a reply box"),
    "main-activity": ("window", s_main_activity, "Show tool activity turned on"),
    "main-last-message": ("window", s_main_last_message,
                          "The session list with the Last message column (#146)"),
    "main-update-ready": ("window", s_main_update_ready,
                          "The status bar with an update waiting"),
    "shortcuts-page": ("dialog", d_shortcuts_page, "Help, Keyboard Shortcuts (formatted page)"),
    "shortcuts-plain": ("dialog", d_shortcuts_plain, "Keyboard Shortcuts as plain text"),
    "user-guide": ("dialog", d_user_guide, "Help, User Guide (formatted page)"),
    "message-formatted": ("dialog", d_message_formatted,
                          "A message read as a formatted page: heading, list, code, table, link"),
    "message-plain": ("dialog", d_message_plain, "The same message as plain text"),
    "settings": ("dialog", d_settings, "Settings"),
    "new-session": ("dialog", d_new_session, "File, New Session"),
    "continue-here": ("dialog", d_continue_here, "Continue Here (a desktop session)"),
    "update-installed": ("dialog", d_update_installed, "After an update is installed"),
    "permission": ("dialog", d_permission, "Claude asks permission to run a command"),
    "question": ("dialog", d_question, "Claude asks questions (one choice and several choices)"),
    "plan": ("dialog", d_plan, "Claude's plan to approve"),
    "manage-groups": ("dialog", d_manage_groups, "File, Manage Groups"),
    "command-picker": ("dialog", d_command_picker, "Insert Command or Skill"),
    "bug-report": ("dialog", d_bug_report, "Help, Report a Bug"),
    "code-blocks": ("dialog", d_code_blocks, "A message's code blocks"),
    "changes": ("dialog", d_changes, "View, Changed Files"),
    "usage": ("dialog", d_usage, "View, Usage and Context"),
    "about-you": ("dialog", d_about_you, "View, What Claude Knows About You"),
    "session-columns": ("dialog", d_session_columns, "View, Session List Columns"),
    "prompts": ("dialog", d_prompts, "File, Prompts"),
    "prompt-edit": ("dialog", d_prompt_edit, "Editing a saved prompt"),
    "rename": ("dialog", d_rename, "Rename Session"),
    "message-box": ("dialog", d_message_box, "A warning message box"),
}

#: Dialog classes the probe deliberately doesn't photograph, and why.
#: ``tests/test_ui_probe.py`` fails on any dialog class in neither list.
NOT_PHOTOGRAPHED = {}

#: Which dialog class each dialog surface shows (checked by the probe at
#: run time, and by the test for coverage).
DIALOG_CLASSES = {
    "shortcuts-page": "FormattedMessageDialog",
    "shortcuts-plain": "ShortcutsDialog",
    "user-guide": "FormattedMessageDialog",
    "message-formatted": "FormattedMessageDialog",
    "message-plain": "MessageDialog",
    "settings": "SettingsDialog",
    "new-session": "NewSessionDialog",
    "continue-here": "NewSessionDialog",
    "update-installed": "UpdateInstalledDialog",
    "permission": "PermissionDialog",
    "question": "QuestionDialog",
    "plan": "PlanDialog",
    "manage-groups": "ManageGroupsDialog",
    "command-picker": "CommandPickerDialog",
    "bug-report": "BugReportDialog",
    "code-blocks": "CodeBlocksDialog",
    "changes": "ChangesDialog",
    "usage": "UsageDialog",
    "about-you": "AboutYouDialog",
    "session-columns": "SessionColumnsDialog",
    "prompts": "PromptsDialog",
    "prompt-edit": "PromptEditDialog",
}


# -- running --------------------------------------------------------------------------------


def _open_modal_dialog():
    for window in wx.GetTopLevelWindows():
        if isinstance(window, wx.Dialog) and window.IsShown() and window.IsModal():
            return window
    return None


def _has_webview(window) -> bool:
    try:
        import wx.html2
    except ImportError:
        return False
    stack = list(window.GetChildren())
    while stack:
        child = stack.pop()
        if isinstance(child, wx.html2.WebView):
            return True
        stack.extend(child.GetChildren())
    return False


def _webview_busy(window) -> bool:
    import wx.html2
    stack = list(window.GetChildren())
    while stack:
        child = stack.pop()
        if isinstance(child, wx.html2.WebView) and child.IsBusy():
            return True
        stack.extend(child.GetChildren())
    return False


def photograph_dialog(opener, out: Path, stem: str) -> dict:
    """Run ``opener`` (which shows a modal dialog, now or a moment later),
    photograph the dialog once it has settled, and cancel it."""
    result = {"kind": "dialog"}
    state = {"seen": None, "since": 0.0, "done": False}

    def tick(_event=None):
        if state["done"]:
            return
        dialog = _open_modal_dialog()
        now = time.time()
        if dialog is None:
            if now - state["started"] > DIALOG_TIMEOUT_SECONDS:
                state["done"] = True
                result["error"] = "no dialog appeared"
            return
        if dialog is not state["seen"]:
            state["seen"], state["since"] = dialog, now
            return
        wait = WEBVIEW_SETTLE_SECONDS if _has_webview(dialog) else SETTLE_SECONDS
        if now - state["since"] < wait or (_has_webview(dialog) and _webview_busy(dialog)
                                           and now - state["since"] < DIALOG_TIMEOUT_SECONDS):
            return
        state["done"] = True
        try:
            result.update(_save(dialog, out, stem))
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"capture failed: {exc}"
        dialog.EndModal(wx.ID_CANCEL)

    timer = wx.Timer()
    timer.Bind(wx.EVT_TIMER, tick)
    state["started"] = time.time()
    timer.Start(150)
    try:
        opener()
        # A dialog opened later (after background work) is caught here.
        end = time.time() + DIALOG_TIMEOUT_SECONDS + 5
        while not state["done"] and time.time() < end:
            wx.GetApp().ProcessPendingEvents()
            wx.YieldIfNeeded()
            tick()
            time.sleep(0.05)
        if not state["done"]:
            result["error"] = "no dialog appeared"
    finally:
        timer.Stop()
    return result


def _save(window, out: Path, stem: str) -> dict:
    png = out / f"{stem}.png"
    method = capture(window, png)
    info = describe(window)
    info["capture"] = method
    (out / f"{stem}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    problems = [f"{c['class']} {c['label'] or c['name']!r}: {p}"
                for c in info["controls"] for p in c["problems"]]
    return {"png": png.name, "json": f"{stem}.json", "title": info["title"],
            "class": info["class"], "capture": method, "problems": problems}


def _dpi_awareness() -> str:
    if not IS_WINDOWS:
        return ""
    try:
        user32 = ctypes.windll.user32
        user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        value = user32.GetAwarenessFromDpiAwarenessContext(user32.GetThreadDpiAwarenessContext())
        return {0: "unaware", 1: "system aware", 2: "per-monitor aware"}.get(value, str(value))
    except Exception:  # noqa: BLE001
        return "unknown"


def _system_appearance() -> dict:
    info = {}
    try:
        appearance = wx.SystemSettings.GetAppearance()
        info["dark"] = appearance.IsDark()
        info["name"] = appearance.GetName()
    except Exception:  # noqa: BLE001
        pass
    if IS_WINDOWS:
        info["high_contrast"] = wx.SystemSettings.GetScreenType() == wx.SYS_SCREEN_NONE or \
            _high_contrast_on()
    return info


def _high_contrast_on() -> bool:
    class HIGHCONTRAST(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwFlags", ctypes.c_uint),
                    ("lpszDefaultScheme", ctypes.c_wchar_p)]
    hc = HIGHCONTRAST(ctypes.sizeof(HIGHCONTRAST), 0, None)
    SPI_GETHIGHCONTRAST = 0x0042
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETHIGHCONTRAST, hc.cbSize, ctypes.byref(hc), 0)
    return bool(hc.dwFlags & 1)


def run(out: Path, tag: str, names, size) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    # Kept before the fakes replace it: the message-box surface shows a real one.
    wx._probe_real_message_box = wx.MessageBox
    results = {}
    with tempfile.TemporaryDirectory(prefix="tcp-probe-") as tmp:
        env = build_world(Path(tmp) / "world")
        frame = build_frame(env)
        frame.SetPosition((20, 20))
        frame.SetSize(size)
        frame.Show()
        frame.Raise()
        wx.SafeYield()
        try:
            for name in [n for n in names if n in SURFACES]:
                kind, function, about = SURFACES[name]
                stem = f"{name}-{tag}" if tag else name
                print(f"  {stem}", flush=True)
                try:
                    if kind == "window":
                        function(frame, env)
                        frame.Layout()
                        _settle(frame)
                        entry = {"kind": "window", **_save(frame, out, stem)}
                    else:
                        opener = function(frame, env)
                        _settle(frame)
                        entry = photograph_dialog(opener, out, stem)
                        expected = DIALOG_CLASSES.get(name)
                        if expected and entry.get("class") and entry["class"] != expected:
                            entry["error"] = f"showed {entry['class']}, expected {expected}"
                except Exception:  # noqa: BLE001
                    entry = {"kind": kind, "error": traceback.format_exc(limit=4)}
                entry["about"] = about
                results[name] = entry
        finally:
            frame.stop_timers()
            frame._pool.shutdown(wait=True)
            wx.GetApp().ProcessPendingEvents()
            frame.Destroy()
            wx.GetApp().ProcessPendingEvents()
        if "main-empty" in names:
            results["main-empty"] = _empty(Path(tmp) / "empty", out, tag, size)
    return results


def _empty(root, out, tag, size):
    """The window with no sessions at all: a first run."""
    env = build_world(root, empty=True)
    frame = build_frame(env, empty=True)
    frame.SetPosition((20, 20))
    frame.SetSize(size)
    frame.Show()
    try:
        _settle(frame, 1.5)
        stem = f"main-empty-{tag}" if tag else "main-empty"
        entry = {"kind": "window", **_save(frame, out, stem)}
    except Exception:  # noqa: BLE001
        entry = {"kind": "window", "error": traceback.format_exc(limit=4)}
    finally:
        frame.stop_timers()
        frame._pool.shutdown(wait=True)
        wx.GetApp().ProcessPendingEvents()
        frame.Destroy()
    entry["about"] = "Main window with no sessions at all (a first run)"
    return entry


def _settle(frame, seconds=SETTLE_SECONDS):
    end = time.time() + seconds
    while time.time() < end:
        wx.GetApp().ProcessPendingEvents()
        wx.YieldIfNeeded()
        time.sleep(0.03)
    frame.Refresh()
    frame.Update()


ALL_NAMES = list(SURFACES) + ["main-empty"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="folder for the pictures and descriptions")
    parser.add_argument("--tag", default="", help="variant label added to each file name, "
                                                  "e.g. light-100")
    parser.add_argument("--surface", action="append", choices=ALL_NAMES,
                        help="only these surfaces (repeatable); all by default")
    parser.add_argument("--size", default="1000x720", help="main window size, WIDTHxHEIGHT")
    parser.add_argument("--list", action="store_true", help="list the surfaces and stop")
    args = parser.parse_args(argv)
    if args.list:
        for name in ALL_NAMES:
            about = SURFACES[name][2] if name in SURFACES else "Main window with no sessions"
            print(f"{name:20} {about}")
        return 0
    if args.out is None:
        parser.error("--out is required")
    width, height = (int(n) for n in args.size.lower().split("x"))
    app = wx.App(False)  # noqa: F841
    names = args.surface or ALL_NAMES
    started = time.time()
    results = run(args.out, args.tag, names, (width, height))
    manifest_path = args.out / (f"manifest-{args.tag}.json" if args.tag else "manifest.json")
    manifest = {
        "tag": args.tag, "platform": sys.platform, "os": platform.platform(),
        "wx": wx.version(), "python": platform.python_version(),
        "dpi_awareness": _dpi_awareness(), "appearance": _system_appearance(),
        "size": [width, height], "seconds": round(time.time() - started, 1),
        "surfaces": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    failed = [n for n, r in results.items() if r.get("error")]
    flagged = [n for n, r in results.items() if r.get("problems")]
    print(f"{len(results) - len(failed)} of {len(results)} surfaces photographed; "
          f"{len(flagged)} with layout problems flagged; manifest: {manifest_path}")
    for name in failed:
        print(f"FAILED {name}: {results[name]['error'].strip().splitlines()[-1]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
