"""The session list's Started column, and Last activity that follows Claude's
work (#209)."""
import json
import os
import time
from datetime import datetime, timezone

from records import assistant_block, lines, text_block, user_text
from thechatplace import hub, platform_paths
from thechatplace.own_store import OwnSession
from thechatplace.sessions import (DESKTOP, FIELD_STARTED, OPTIONAL_FIELDS, SessionInfo,
                                   describe_age, describe_started)
from thechatplace.transcript import SessionFactsCache, record_time_ms

NOW = 1_800_000_000_000
DAY = 24 * 60 * 60_000
#: 2026-10-06 12:00 UTC, as a transcript writes it and in milliseconds.
STAMP = "2026-10-06T12:00:00.000Z"
STAMP_MS = int(datetime(2026, 10, 6, 12, tzinfo=timezone.utc).timestamp() * 1000)


def test_started_reads_like_last_activity_and_says_nothing_when_unknown():
    assert describe_started(NOW - 2 * DAY, NOW) == "started 2 days ago"
    assert describe_started(NOW - 30_000, NOW) == "started just now"
    assert describe_started(0, NOW) == ""
    assert describe_age(NOW - 3 * 60 * 60_000, NOW) == "active 3 hours ago"
    assert describe_age(0, NOW) == "no activity recorded"


def test_started_is_a_column_you_choose_and_off_by_default():
    info = SessionInfo(DESKTOP, "x", "Fix the build", "C:\\G\\Repo", "x",
                       last_activity_ms=NOW - 60_000, created_ms=NOW - DAY)
    assert FIELD_STARTED in OPTIONAL_FIELDS
    assert "started" not in info.list_line(NOW)
    assert info.list_line(NOW, ["title", "started", "activity"]) == (
        "Fix the build, started yesterday, active 1 minute ago")


def test_a_records_time_in_milliseconds():
    assert record_time_ms({"timestamp": STAMP}) == STAMP_MS
    assert record_time_ms({"timestamp": "not a time"}) == 0
    assert record_time_ms({}) == 0


def test_a_terminal_sessions_start_is_its_first_records_time(tmp_path):
    path = tmp_path / "t.jsonl"
    first = dict(user_text("Tidy up"), entrypoint="cli", timestamp=STAMP)
    later = dict(assistant_block(text_block("Done."), "m1"), entrypoint="cli",
                 timestamp="2026-10-07T09:00:00.000Z")
    path.write_text("\n".join(lines(first, later)) + "\n", encoding="utf-8")
    assert SessionFactsCache().get(path).started_ms == STAMP_MS


def test_desktop_and_own_sessions_know_when_they_began(tmp_path):
    own = OwnSession("own-1", "Mine", "C:\\G\\Repo", created_ms=NOW - DAY,
                     last_activity_ms=NOW)
    assert own.to_info().created_ms == NOW - DAY
    folder = tmp_path / "d" / "acct" / "org"
    folder.mkdir(parents=True)
    (folder / "local_a.json").write_text(json.dumps({
        "sessionId": "local_a", "cliSessionId": "cli-a", "title": "Desktop one",
        "cwd": "C:\\G\\Repo", "createdAt": NOW - 3 * DAY, "lastActivityAt": NOW - DAY}),
        encoding="utf-8")
    snap = hub.collect([], set(), desktop_dir=tmp_path / "d", live_dir=tmp_path / "l")
    (desktop,) = [s for s in snap.sessions if s.key == "local_a"]
    assert desktop.created_ms == NOW - 3 * DAY


def test_last_activity_follows_the_transcript_through_a_long_turn(tmp_path, monkeypatch):
    """Visual Review read "active 3 hours ago" while its transcript was being
    written: The Chat Place only noted the time when it started the turn."""
    projects = tmp_path / "projects"
    monkeypatch.setattr(platform_paths, "projects_dir", lambda: projects)
    folder = projects / platform_paths.encode_cwd("C:\\G\\Repo")
    folder.mkdir(parents=True)
    path = folder / "own-1.jsonl"
    path.write_text("\n".join(lines(user_text("Go"))) + "\n", encoding="utf-8")
    written = int(time.time() * 1000)
    os.utime(path, ns=(written * 1_000_000, written * 1_000_000))
    three_hours_ago = written - 3 * 60 * 60_000
    own = OwnSession("own-1", "Visual Review", "C:\\G\\Repo", last_activity_ms=three_hours_ago)
    stale = OwnSession("own-2", "No transcript", "C:\\G\\Elsewhere", last_activity_ms=123)
    snap = hub.collect([own, stale], {"own-1"}, desktop_dir=tmp_path / "d",
                       live_dir=tmp_path / "l")
    by_key = {s.key: s.last_activity_ms for s in snap.sessions}
    assert by_key["own:own-1"] == written
    assert by_key["own:own-2"] == 123  # nothing on disk: the stored time stands


def test_an_older_transcript_never_moves_last_activity_back(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    monkeypatch.setattr(platform_paths, "projects_dir", lambda: projects)
    folder = projects / platform_paths.encode_cwd("C:\\G\\Repo")
    folder.mkdir(parents=True)
    path = folder / "own-1.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    os.utime(path, ns=(1_000_000_000_000_000, 1_000_000_000_000_000))  # long ago
    own = OwnSession("own-1", "Fresh", "C:\\G\\Repo", last_activity_ms=NOW)
    snap = hub.collect([own], set(), desktop_dir=tmp_path / "d", live_dir=tmp_path / "l")
    assert snap.sessions[0].last_activity_ms == NOW
