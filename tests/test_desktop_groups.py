"""The Claude desktop app's own session groups (#51)."""
import json

from theclaudehub.desktop_groups import CONFIG_NAME, load_desktop_groups


def _config(tmp_path, scopes):
    sessions = tmp_path / "claude-code-sessions"
    sessions.mkdir()
    prefs = {"preferences": {"epitaxyPrefs": {"dframe-group-scopes": scopes}}}
    (tmp_path / CONFIG_NAME).write_text(json.dumps(prefs), encoding="utf-8")
    return sessions


def test_groups_and_their_sessions_in_the_apps_order(tmp_path):
    folder = _config(tmp_path, {"acct/org": {
        "groups": [{"id": "cg-1", "name": "IDT"}, {"id": "cg-2", "name": "Random"},
                   {"id": "cg-3", "name": "  "}],
        "assignments": {"code:local_a": "cg-1", "code:local_b": "cg-2",
                        "code:local_c": "cg-gone", "chat:x": "cg-1"},
        "order": {}}})
    groups = load_desktop_groups([folder])
    assert groups.names == ["IDT", "Random"]
    assert groups.by_session == {"local_a": "IDT", "local_b": "Random"}


def test_anything_unexpected_means_no_groups(tmp_path):
    assert load_desktop_groups([tmp_path / "missing" / "claude-code-sessions"]).names == []
    folder = tmp_path / "claude-code-sessions"
    folder.mkdir()
    for raw in ("not json", json.dumps({"preferences": {}}),
                json.dumps({"preferences": {"epitaxyPrefs": {"dframe-group-scopes": []}}}),
                json.dumps({"preferences": {"epitaxyPrefs": {"dframe-group-scopes": {
                    "s": {"groups": "nope", "assignments": []}}}}})):
        (tmp_path / CONFIG_NAME).write_text(raw, encoding="utf-8")
        groups = load_desktop_groups([folder])
        assert (groups.names, groups.by_session) == ([], {})
