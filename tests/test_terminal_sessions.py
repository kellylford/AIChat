"""Sessions started by typing claude in a terminal (#158)."""
import json
import os

import pytest

from records import assistant_block, lines, other, text_block, user_text
from thechatplace import claude_cli, hub, links, platform_paths
from thechatplace.own_store import OwnSession
from thechatplace.sessions import (IDLE, TERMINAL, VIEW_DESKTOP, VIEW_OWN, VIEW_TERMINAL,
                                   WORKING, LiveStatus, in_view, load_terminal_sessions)
from thechatplace.transcript import SessionFactsCache

CWD = "C:\\Users\\someone\\Documents"


def write(projects, cli, *records, cwd=CWD, entrypoint="cli"):
    """A transcript as Claude Code writes one, every record from ``entrypoint``."""
    folder = projects / platform_paths.encode_cwd(cwd)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{cli}.jsonl"
    stamped = [dict(r, entrypoint=entrypoint, cwd=cwd) if r.get("type") in ("user", "assistant")
               else r for r in records]
    path.write_text("\n".join(lines(*stamped)) + "\n", encoding="utf-8")
    return path


def append(path, *records):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines(*records)) + "\n")
    # A later write in the same clock tick still counts as a change.
    stat = os.stat(path)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


# -- what a transcript says ---------------------------------------------------------------


def test_facts_of_a_terminal_session(tmp_path):
    path = write(tmp_path, "t1", other("agent-name", agentName="x"),
                 user_text("<command-name>/clear</command-name>"),
                 user_text("Tidy up my notes folder\nand sort it"),
                 assistant_block(text_block("Done."), "m1"))
    facts = SessionFactsCache().get(path)
    assert facts.terminal and facts.cwd == CWD
    # A harness record isn't your first message; the first line of yours is.
    assert facts.title == "Tidy up my notes folder"


def test_a_title_given_later_wins_and_is_read_incrementally(tmp_path):
    path = write(tmp_path, "t1", user_text("First thing"))
    cache = SessionFactsCache()
    assert cache.get(path).title == "First thing"
    append(path, other("ai-title", aiTitle="Sorting notes"))
    assert cache.get(path).title == "Sorting notes"
    before = cache.bytes_read
    append(path, other("custom-title", customTitle="  My   notes "))
    assert cache.get(path).title == "My notes"
    # Only what was added was read.
    assert cache.bytes_read - before < 200
    read = cache.bytes_read
    assert cache.get(path).title == "My notes"  # unchanged: not read at all
    assert cache.bytes_read == read


def test_other_transcripts_are_left_after_their_first_records(tmp_path):
    """A claude -p run, the desktop app's, or a subagent's: not a terminal
    session, however long, and not read past the start."""
    big = [assistant_block(text_block("x" * 1000), f"m{i}") for i in range(300)]
    for entrypoint in ("sdk-cli", "claude-desktop", "claude-vscode"):
        path = write(tmp_path, f"s-{entrypoint}", user_text("hi"), *big, entrypoint=entrypoint)
        cache = SessionFactsCache(chunk=4096)
        facts = cache.get(path)
        assert not facts.terminal and facts.entrypoint == entrypoint
        assert cache.bytes_read <= 4096
        append(path, other("custom-title", customTitle="Renamed"))
        assert cache.get(path).custom_title == ""  # nothing more is read


def test_a_line_still_being_written_waits(tmp_path):
    path = write(tmp_path, "t1", other("ai-title", aiTitle="Old"))
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(user_text("Typed", entrypoint="cli", cwd=CWD))[:30])
    cache = SessionFactsCache()
    assert cache.get(path).entrypoint == ""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(user_text("Typed", entrypoint="cli", cwd=CWD))[30:] + "\n")
    stat = os.stat(path)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    facts = cache.get(path)
    assert facts.terminal and facts.first_prompt == "Typed" and facts.title == "Old"


def test_a_first_prompt_longer_than_a_piece_is_still_read(tmp_path):
    """A pasted log as the first message: longer than what's read at a time,
    and the record that says whose the transcript is."""
    path = write(tmp_path, "t1", user_text("Big paste " + "p" * 40_000))
    cache = SessionFactsCache(chunk=4096, first_chunk=1024)
    facts = cache.get(path)
    assert facts.terminal and facts.title.startswith("Big paste pppp")
    append(path, user_text("Second", entrypoint="cli", cwd=CWD),
           other("custom-title", customTitle="Named"))
    assert cache.get(path).title == "Named"


def test_a_long_session_is_read_at_its_start_and_end_only(tmp_path):
    """A terminal session's whole transcript isn't read: its start says
    whose it is and its first prompt, its end its newest title and folder."""
    middle = [assistant_block(text_block("y" * 2000), f"m{i}") for i in range(500)]
    moved = CWD + "\\.claude\\worktrees\\fix"
    path = write(tmp_path, "t1", user_text("Start here"), other("ai-title", aiTitle="Old"),
                 *middle)
    append(path, other("ai-title", aiTitle="Newest title"),
           dict(user_text("Later", entrypoint="cli"), cwd=moved))
    cache = SessionFactsCache(tail=64 * 1024)
    facts = cache.get(path)
    size = path.stat().st_size
    assert size > 1_000_000 and cache.bytes_read < 200 * 1024
    assert facts.first_prompt == "Start here" and facts.title == "Newest title"
    assert facts.cwd == moved and facts.modified_ms > 0


def test_a_file_replaced_with_one_the_same_size_is_read_again(tmp_path):
    path = write(tmp_path, "t1", user_text("Hi"), other("custom-title", customTitle="AAAA"))
    cache = SessionFactsCache()
    assert cache.get(path).title == "AAAA"
    write(tmp_path, "t1", user_text("Ho"), other("custom-title", customTitle="BBBB"))
    stat = os.stat(path)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert cache.get(path).title == "BBBB"


def test_a_desktop_session_carried_on_in_a_terminal_isnt_one(tmp_path):
    """Its transcript starts as the desktop app's, so it stays the desktop
    app's even after claude --resume in a terminal adds to it."""
    path = write(tmp_path, "t1", user_text("From the app"), entrypoint="claude-desktop")
    append(path, user_text("Then the terminal", entrypoint="cli", cwd=CWD))
    assert not SessionFactsCache().get(path).terminal


def test_a_rewritten_or_vanished_file(tmp_path):
    path = write(tmp_path, "t1", user_text("A long first message " * 20),
                 other("custom-title", customTitle="Old name"))
    cache = SessionFactsCache()
    assert cache.get(path).title == "Old name"
    write(tmp_path, "t1", user_text("Short"))
    assert cache.get(path).title == "Short"
    path.unlink()
    assert cache.get(path) is None


def test_sidechain_and_unreadable_lines_dont_count(tmp_path):
    folder = tmp_path / "proj"
    folder.mkdir()
    path = folder / "t1.jsonl"
    side = user_text("Subagent prompt", entrypoint="sdk-cli", isSidechain=True)
    path.write_text("not json\n" + json.dumps(side) + "\n"
                    + json.dumps(user_text("Mine", entrypoint="cli", cwd=CWD)) + "\n",
                    encoding="utf-8")
    facts = SessionFactsCache().get(path)
    assert facts.terminal and facts.title == "Mine"


# -- the list -----------------------------------------------------------------------------


def test_load_lists_only_terminal_sessions_nobody_else_claims(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_paths, "projects_dir", lambda: tmp_path)
    write(tmp_path, "term-1", user_text("Mine from the terminal"))
    write(tmp_path, "term-busy", user_text("Running now"), cwd="D:\\Work")
    write(tmp_path, "desk-1", user_text("Desktop"))  # a cli entrypoint, but claimed
    write(tmp_path, "script-1", user_text("From a script"), entrypoint="sdk-cli")
    sub = tmp_path / platform_paths.encode_cwd(CWD) / "term-1" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-1.jsonl").write_text("\n".join(lines(user_text("x", entrypoint="cli"))) + "\n",
                                       encoding="utf-8")
    write(tmp_path, "bad id!", user_text("Unsafe"))
    live = {"term-busy": LiveStatus("busy", 5, 0)}
    found = load_terminal_sessions(tmp_path, live, {"desk-1"}, SessionFactsCache())
    by_id = {s.cli_session_id: s for s in found}
    assert set(by_id) == {"term-1", "term-busy"}
    one = by_id["term-1"]
    assert (one.source, one.key, one.title, one.cwd, one.state) == (
        TERMINAL, "terminal:term-1", "Mine from the terminal", CWD, IDLE)
    assert one.is_terminal and not one.is_own and not one.can_open_in_claude
    assert one.last_activity_ms > 0 and one.repo == "Documents"
    assert one.transcript_path() == tmp_path / platform_paths.encode_cwd(CWD) / "term-1.jsonl"
    assert by_id["term-busy"].state == WORKING
    assert one.list_line(fields=["title", "kind"]) == "Mine from the terminal, terminal session"


def test_missing_projects_folder_lists_nothing(tmp_path):
    assert load_terminal_sessions(tmp_path / "none", {}, set(), SessionFactsCache()) == []


def test_collect_adds_terminal_sessions_once(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    write(projects, "term-1", user_text("From the terminal"))
    write(projects, "own-1", user_text("An own session resumed in a terminal"))
    monkeypatch.setattr(hub, "terminal_projects_dir", lambda: projects)
    desktop = tmp_path / "d" / "local_a" / "org"
    desktop.mkdir(parents=True)
    (desktop / "local_a.json").write_text(json.dumps(
        {"sessionId": "local_a", "cliSessionId": "desk-1", "cwd": CWD, "title": "Desktop one"}),
        encoding="utf-8")
    write(projects, "desk-1", user_text("Desktop's"))
    snap = hub.collect([OwnSession("own-1", "Mine", CWD)], set(), desktop_dir=tmp_path / "d",
                       live_dir=tmp_path / "l")
    keys = sorted(s.key for s in snap.sessions)
    assert keys == ["local_a", "own:own-1", "terminal:term-1"]


def test_views_and_kind():
    from thechatplace.sessions import SessionInfo, DESKTOP, OWN
    term = SessionInfo(TERMINAL, "terminal:t", "T", CWD, "t")
    desk = SessionInfo(DESKTOP, "local_d", "D", CWD, "d", desktop_session_id="local_d")
    own = SessionInfo(OWN, "own:o", "O", CWD, "o")
    assert [in_view(s, VIEW_TERMINAL) for s in (term, desk, own)] == [True, False, False]
    assert [in_view(s, VIEW_DESKTOP) for s in (term, desk, own)] == [False, True, False]
    assert [in_view(s, VIEW_OWN) for s in (term, desk, own)] == [False, False, True]
    assert term.field_values()["kind"] == "terminal session"


def test_terminal_sessions_have_links():
    from thechatplace.sessions import SessionInfo, DESKTOP
    tid = "aaaaaaaa-1111-4222-8333-444444444444"
    term = SessionInfo(TERMINAL, f"terminal:{tid}", "T", CWD, tid)
    desk = SessionInfo(DESKTOP, "local_d", "D", CWD, "cli-d", desktop_session_id="local_d")
    assert links.session_link(term) == links.PREFIX + tid
    assert links.find_session([desk, term], tid.upper()) is term
    # A terminal session's id never finds a desktop one by its cli id.
    assert links.find_session([desk], "cli-d") is None


def test_a_terminal_session_is_never_resumed():
    """Read-only: only The Chat Place's own sessions are resumed; a terminal
    session can only be copied with Continue Here."""
    with pytest.raises(claude_cli.ResumeRefused):
        claude_cli.check_resume_allowed("term-1", own_ids={"own-1"}, desktop_ids=set())
    command = claude_cli.build_fork_command("claude.exe", "term-1", "new-1", "Copy", "default",
                                            "", taken_ids={"own-1"}, cowork_ids=set())
    assert command[command.index("--resume") + 1] == "term-1" and "--fork-session" in command


def test_waiting_in_the_terminal_needs_you(tmp_path):
    """Claude Code says "waiting" (and what for) while a permission, question
    or other dialog is up in the terminal; at its prompt it says "idle"."""
    (tmp_path / "live").mkdir()
    (tmp_path / "live" / "10.json").write_text(json.dumps(
        {"pid": 10, "sessionId": "t-wait", "status": "waiting", "waitingFor": "dialog  open"}))
    (tmp_path / "live" / "11.json").write_text(json.dumps(
        {"pid": 11, "sessionId": "t-idle", "status": "idle"}))
    from thechatplace.sessions import NEEDS_YOU, load_live_status
    live = load_live_status(tmp_path / "live", alive=lambda pid: True, started=lambda pid: None)
    assert live["t-wait"].waiting_for == "dialog open"
    for cli in ("t-wait", "t-idle", "t-gone"):
        write(tmp_path / "p", cli, user_text(f"Prompt {cli}"))
    found = {s.cli_session_id: s for s in load_terminal_sessions(tmp_path / "p", live, set(),
                                                                 SessionFactsCache())}
    assert (found["t-wait"].state, found["t-wait"].detail) == (NEEDS_YOU, "dialog open")
    assert found["t-idle"].state == IDLE and found["t-gone"].state == IDLE
    live["t-idle"] = LiveStatus("waiting", 11)
    again = load_terminal_sessions(tmp_path / "p", live, set(), SessionFactsCache())
    assert {s.cli_session_id: s.detail for s in again}["t-idle"] == "waiting for you"


def test_a_session_with_no_prompt_has_a_title_all_the_same(tmp_path):
    write(tmp_path, "t1", user_text("<command-name>/usage</command-name>"))
    found = load_terminal_sessions(tmp_path, {}, set(), SessionFactsCache())
    assert [s.title for s in found] == ["Untitled terminal session in Documents"]
