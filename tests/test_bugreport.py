"""Reporting a bug (#28)."""
import urllib.parse

from thechatplace import bugreport
from thechatplace.speech import SpeechSettings


def _report(**overrides):
    values = dict(summary="F6 skips the reply box", what_happened="It went to the status bar.",
                  expected="The reply box", steps="1. Load a session\n2. Press F6 twice",
                  environment=[("The Chat Place", "0.1.0"), ("Windows", "11")])
    values.update(overrides)
    return bugreport.BugReport(**values)


def test_report_text_has_each_section_and_the_environment():
    text = bugreport.report_text(_report())
    assert text.startswith("### What happened\nIt went to the status bar.\n")
    assert "### What I expected\nThe reply box" in text
    assert "### Steps to reproduce\n1. Load a session\n2. Press F6 twice" in text
    assert "### Environment\n- The Chat Place: 0.1.0\n- Windows: 11" in text


def test_optional_sections_are_left_out_when_empty():
    text = bugreport.report_text(_report(expected=" ", steps=""))
    assert "What I expected" not in text and "Steps to reproduce" not in text


def test_new_issue_url_is_prefilled_and_cut_to_fit():
    url = bugreport.new_issue_url(_report())
    assert url.startswith(f"https://github.com/{bugreport.REPO}/issues/new?")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["title"] == ["F6 skips the reply box"] and query["labels"] == ["bug"]
    for words in ("x " * 5000, "é" * 4000):  # non-ASCII grows a lot when encoded
        long = bugreport.new_issue_url(_report(what_happened=words))
        query = urllib.parse.urlparse(long).query
        body = urllib.parse.parse_qs(query)["body"][0]
        assert len(urllib.parse.quote(body)) <= bugreport.MAX_URL_BODY
        assert "clipboard" in body and "### Environment" in body  # the environment survives


def test_environment_names_no_people_or_paths():
    facts = bugreport.environment(SpeechSettings(), {"desktop app": 3, "Chat Place": 1},
                                  claude_version="2.1.286 (Claude Code)")
    labels = [label for label, _value in facts]
    assert labels[:5] == ["The Chat Place", "Windows", "Python", "wxPython", "Claude Code"]
    assert ("Sessions listed", "3 desktop app, 1 Chat Place") in facts
    text = " ".join(str(value) for _label, value in facts)
    assert "Users" not in text and "\\" not in text


def test_only_a_version_number_is_kept(monkeypatch):
    import subprocess

    class Out:
        def __init__(self, stdout):
            self.stdout, self.stderr = stdout, ""
    monkeypatch.setattr(bugreport.platform_paths, "claude_executable", lambda: "claude.exe")
    for printed, kept in (("2.1.286 (Claude Code)\n", "2.1.286 (Claude Code)"),
                          ("Error: C:\\Users\\kelly\\x not found", "unknown"),
                          ("", "unknown")):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: Out(printed))
        assert bugreport.claude_code_version() == kept
