"""Layout checks that need no pictures (#155): every dialog, and the main
window in its main states, laid out hidden, with no text cut off, no
controls on top of each other and nothing outside the window.

The measuring is the visual probe's (``tools/ui_probe.describe``), so what
fails here is what the probe flags in its pictures. A failure names the
control and the problem; ``tools/ui_probe_vm.ps1`` in the test VM shows
what it looks like.

Problems already filed are listed in ``KNOWN`` with their issue, so they
don't fail the build while they wait. A new problem fails, and so does a
known one that has gone, so its entry is removed when the issue is fixed.
"""
import inspect
import re
import sys
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import fake_env  # noqa: E402
import ui_probe  # noqa: E402
from thechatplace import speech  # noqa: E402
from thechatplace.claude_cli import PermissionRequest  # noqa: E402
from thechatplace.codeblocks import find_code_blocks  # noqa: E402

#: (where, pattern matching the problem, issue). ``where`` is a dialog
#: class, or "main" for the main window.
KNOWN = [
    ("main", r"^Button '\d+ sessions? needs? you': text cut off", 175),
    # The heading and the messages label, with a long session title.
    ("main", r"^StaticText '.*(read-only|default model)\.': text cut off", 176),
    ("main", r"^StaticText '&Messages in .*': text cut off", 176),
    # "Cloned into <folder>", with a long folder.
    ("GitHubRepoDialog", r"^StaticText \"Cloned into ", 176),
    ("SettingsDialog", r"^CheckBox \"Turn on Remote &Control", 176),
    ("BugReportDialog", r"^StaticText \"Open on GitHub needs access", 176),
    ("SessionColumnsDialog", r"^StaticText 'Each session in the list is read as one line", 176),
]

#: Dialogs measured only in the probe's pictures, and why.
NOT_MEASURED = {
    # Its page is drawn by WebView2 in another process; the tests have no web view.
    "FormattedMessageDialog",
}

#: Every known problem seen, so the last test can say which have gone.
_seen_known = set()


@pytest.fixture(scope="module")
def app():
    instance = wx.App(False)
    yield instance


@pytest.fixture
def frame(tmp_path, monkeypatch, app):
    env = ui_probe.build_world(tmp_path, monkeypatch.setattr, formatted_view=False)
    window = ui_probe.build_frame(env)
    window.SetSize((1000, 720))
    yield window
    ui_probe.close_frame(window)


def problems(window, where) -> list:
    """The probe's flags for ``window``, less the known ones."""
    window.Layout()
    info = ui_probe.describe(window)
    found = []
    for control in info["controls"]:
        for problem in control["problems"]:
            text = f"{control['class']} {control['label'] or control['name']!r}: {problem}"
            known = [k for k in KNOWN if k[0] == where and re.search(k[1], text)]
            _seen_known.update(known)
            if not known:
                found.append(text)
    return found


def _request(tool, tool_input):
    return PermissionRequest("r1", tool, tool_input, suggestions=[])


LONG_TITLE = ("A session whose title goes on and on to show what a very long title does to the "
              "session list and the heading above the messages")


def _dialogs(frame):
    """Our dialog class name -> a function making it, with made-up content
    like a real session's."""
    from thechatplace.ui import dialogs as d
    from thechatplace.ui.main_frame import PERMISSION_MODES
    sample = frame._snapshot.sessions[0]
    code = ui_probe.LONG_MESSAGE
    return {
        "ShortcutsDialog": lambda: d.ShortcutsDialog(frame),
        "NewSessionDialog": lambda: d.NewSessionDialog(frame, sample.cwd, continue_from=LONG_TITLE),
        "GitHubRepoDialog": lambda: d.GitHubRepoDialog(frame, "gh.exe", sample.cwd),
        "SettingsDialog": lambda: d.SettingsDialog(frame, speech.SpeechSettings(),
                                                   speech.default_options()),
        "MessageDialog": lambda: d.MessageDialog(frame, "Claude", code * 5),
        "UpdateInstalledDialog": lambda: d.UpdateInstalledDialog(frame, "0.2.0", lambda: None),
        "PermissionDialog": lambda: d.PermissionDialog(frame, LONG_TITLE, _request(
            "Bash", {"command": "git push origin release/0.2"})),
        "QuestionDialog": lambda: d.QuestionDialog(frame, "Visual probe", _request(
            "AskUserQuestion", {"questions": [
                {"header": "Branch", "question": "Which name should the release branch use?",
                 "options": [{"label": "release/0.2", "description": "Matches the last one"},
                             {"label": "v0.2-prep"}]},
                {"header": "Checks", "question": "Which checks first?", "multiSelect": True,
                 "options": [{"label": "Unit tests"}, {"label": "Smoke test"}]}]})),
        "PlanDialog": lambda: d.PlanDialog(
            frame, "Visual probe", _request("ExitPlanMode", {"plan": "# Plan\n1. Go"}),
            [(v, label) for v, label in PERMISSION_MODES if v != "plan"], "acceptEdits"),
        "ManageGroupsDialog": lambda: d.ManageGroupsDialog(frame, frame.groups, {}),
        "CommandPickerDialog": lambda: d.CommandPickerDialog(frame, fake_env.FAKE_COMMANDS),
        "BugReportDialog": lambda: d.BugReportDialog(frame, ["The Chat Place: 0.1.0",
                                                             "Windows 11"]),
        "CodeBlocksDialog": lambda: d.CodeBlocksDialog(frame, find_code_blocks(code),
                                                       lambda block: None),
        "ChangesDialog": lambda: d.ChangesDialog(frame, LONG_TITLE, [], [], str),
        "UsageDialog": lambda: d.UsageDialog(frame, ["Context: 40% used.",
                                                     "Five-hour limit: 12% used."],
                                             lambda text, one: None),
        "AboutYouDialog": lambda: d.AboutYouDialog(frame, [], lambda done: None,
                                                   lambda p: None, lambda p: None,
                                                   lambda p: None),
        "SessionColumnsDialog": lambda: d.SessionColumnsDialog(
            frame, frame.speech.session_fields, sample, lambda text: None),
        "PromptEditDialog": lambda: d.PromptEditDialog(frame, "Edit Prompt", "Review",
                                                       "Review this change."),
        "PromptsDialog": lambda: d.PromptsDialog(frame, frame.prompts, lambda text: None),
    }


def _our_dialogs():
    from thechatplace.ui import dialogs
    return sorted(name for name, cls in inspect.getmembers(dialogs, inspect.isclass)
                  if issubclass(cls, wx.Dialog) and cls.__module__ == dialogs.__name__)


def test_every_dialog_is_measured_or_says_why_not(frame):
    assert set(_our_dialogs()) == set(_dialogs(frame)) | NOT_MEASURED


@pytest.mark.parametrize("name", [n for n in _our_dialogs() if n not in NOT_MEASURED])
def test_dialog_lays_out_cleanly(frame, name):
    dialog = _dialogs(frame)[name]()
    try:
        assert problems(dialog, name) == []
    finally:
        dialog.Destroy()


@pytest.mark.parametrize("size", [(1000, 720), (800, 600)])
@pytest.mark.parametrize("session", [None, "Visual probe", "Fix the flaky upload test",
                                     "A session whose title"])
def test_main_window_lays_out_cleanly(frame, size, session):
    if session:
        ui_probe._open(frame, session)
    frame.SetSize(size)
    assert problems(frame, "main") == []


def test_each_known_problem_is_still_there():
    """Runs last in this file: a known problem nobody saw has been fixed, so
    its line in KNOWN (and its issue) can go. Only meaningful when the whole
    file runs, so it skips under -k."""
    if not _seen_known:
        pytest.skip("run the whole file to check KNOWN")
    gone = [f"{where}: {pattern} (#{issue})" for where, pattern, issue in KNOWN
            if (where, pattern, issue) not in _seen_known]
    assert gone == [], "fixed? remove these from KNOWN and close their issues"
