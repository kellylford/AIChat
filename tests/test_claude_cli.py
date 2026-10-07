import io
import json
import sys
import threading
from pathlib import Path

import pytest

from thechatplace import claude_cli as cli
from thechatplace import platform_paths
from thechatplace.claude_cli import (ResumeRefused, StreamParser, TurnRunner,
                                     build_new_command, build_resume_command,
                                     check_resume_allowed, child_environment)
from markers import windows_paths  # noqa: E402

EXE = "C:\\bin\\claude.exe"
OWN = {"aaaa-1111"}
DESKTOP = {"dddd-2222"}
FLAGS = ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
PROMPTS = ["--permission-prompts", "host", "--permission-prompt-tool", "stdio"]


# -- command construction --------------------------------------------------------


def test_new_command():
    command = build_new_command(EXE, "aaaa-1111", "  My   title ", "auto")
    assert command == [EXE, *FLAGS, "--permission-mode", "auto", *PROMPTS,
                       "--session-id", "aaaa-1111", "--name", "My title"]


def test_new_command_without_title_and_other_modes():
    for mode in ("acceptEdits", "manual", "plan"):
        command = build_new_command(EXE, "aaaa-1111", "", mode)
        assert "--name" not in command
        assert command[command.index("--permission-mode") + 1] == mode


def test_old_default_mode_name_becomes_manual():
    command = build_resume_command(EXE, "aaaa-1111", "default", OWN, DESKTOP)
    assert command[command.index("--permission-mode") + 1] == "manual"


def test_never_bare_prompts_come_to_us_and_prompt_not_on_command_line():
    for command in (build_new_command(EXE, "aaaa-1111", "t", "auto"),
                    build_resume_command(EXE, "aaaa-1111", "auto", OWN, DESKTOP)):
        assert "--bare" not in command
        assert "-p" in command
        assert command[command.index("--permission-prompts") + 1] == "host"
        assert command[command.index("--permission-prompt-tool") + 1] == "stdio"


def test_unknown_permission_mode_refused():
    with pytest.raises(ValueError):
        build_new_command(EXE, "aaaa-1111", "t", "bypassPermissions")
    with pytest.raises(ValueError):
        build_resume_command(EXE, "aaaa-1111", "yolo", OWN, DESKTOP)


def test_new_command_rejects_bad_id():
    with pytest.raises(ValueError):
        build_new_command(EXE, "--resume", "t", "auto")


def test_resume_command_for_own_session():
    assert build_resume_command(EXE, "aaaa-1111", "plan", OWN, DESKTOP) == [
        EXE, *FLAGS, "--permission-mode", "plan", *PROMPTS,
        "--resume", "aaaa-1111"]


def test_model_goes_on_every_turn():
    new = build_new_command(EXE, "aaaa-1111", "t", "auto", "opus")
    resumed = build_resume_command(EXE, "aaaa-1111", "auto", OWN, DESKTOP, model="opus")
    for command in (new, resumed):
        assert command[command.index("--model") + 1] == "opus"
    # A full model name works too.
    command = build_resume_command(EXE, "aaaa-1111", "auto", OWN, DESKTOP,
                                   model="claude-opus-5-5")
    assert command[command.index("--model") + 1] == "claude-opus-5-5"


def test_default_model_passes_no_model_flag():
    assert "--model" not in build_new_command(EXE, "aaaa-1111", "t", "auto", "")
    assert "--model" not in build_resume_command(EXE, "aaaa-1111", "auto", OWN, DESKTOP)


@pytest.mark.parametrize("model", ["--dangerously-skip-permissions", "-x", "opus sonnet",
                                   "a;b", "x" * 101, "sonnet[1m]",
                                   "claude-opus-4-1@20250805",
                                   "us.anthropic.claude-opus-4-1-v1:0"])
def test_unsafe_model_name_refused(model):
    with pytest.raises(ValueError):
        build_new_command(EXE, "aaaa-1111", "t", "auto", model)


def test_model_labels():
    assert cli.model_label("") == "the default model"
    assert cli.model_label("opus") == "Opus"
    assert cli.model_label("claude-opus-5-5") == "claude-opus-5-5"
    assert [value for value, _label in cli.MODELS] == ["", "opus", "sonnet", "haiku"]
    # Fable can bill usage credits without asking in -p mode.
    assert "fable" not in cli.MODEL_LABELS


# -- the desktop --resume guard ------------------------------------------------------


def test_resume_refused_for_desktop_cli_id():
    with pytest.raises(ResumeRefused, match="desktop app"):
        build_resume_command(EXE, "dddd-2222", "auto", OWN | DESKTOP, DESKTOP)


def test_resume_refused_for_local_id_even_if_listed_as_own():
    with pytest.raises(ResumeRefused, match="desktop app session id"):
        build_resume_command(EXE, "local_abc", "auto", {"local_abc"}, set())


def test_resume_refused_for_unknown_session():
    with pytest.raises(ResumeRefused, match="only sends"):
        check_resume_allowed("eeee-3333", OWN, DESKTOP)


@pytest.mark.parametrize("bad", ["", "../x", "--print", "a b", None])
def test_resume_refused_for_malformed_ids(bad):
    with pytest.raises(ResumeRefused):
        check_resume_allowed(bad, OWN | {bad} if bad else OWN, DESKTOP)


# -- environment ---------------------------------------------------------------------


def test_child_environment_strips_session_and_billing_vars_only():
    env = child_environment({
        "PATH": "x", "USERPROFILE": "u",
        "ANTHROPIC_API_KEY": "secret", "ANTHROPIC_AUTH_TOKEN": "t",
        "ANTHROPIC_BASE_URL": "http://localhost", "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDECODE": "1", "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH": "1",
        "CLAUDE_CODE_SESSION_ID": "s", "CLAUDE_CODE_OAUTH_TOKEN": "o",
        "claude_code_entrypoint": "lower",
        # Families a host session sets, including names not in the list yet.
        "CLAUDE_CODE_SDK_FUTURE_THING": "1", "CLAUDE_CODE_HOST_PORT": "1",
        "claude_code_messaging_new": "1",
        "CLAUDE_CODE_GIT_BASH_PATH_EXTRA": "kept",
        # Chosen by the user: kept.
        "CLAUDE_CONFIG_DIR": "D:/c", "CLAUDE_CODE_GIT_BASH_PATH": "C:/Git/bash.exe",
        "HTTPS_PROXY": "http://proxy", "API_TIMEOUT_MS": "60000",
        "ANTHROPIC_MODEL": "opus",
    })
    assert env == {"PATH": "x", "USERPROFILE": "u", "CLAUDE_CONFIG_DIR": "D:/c",
                   "CLAUDE_CODE_GIT_BASH_PATH_EXTRA": "kept",
                   "CLAUDE_CODE_GIT_BASH_PATH": "C:/Git/bash.exe",
                   "HTTPS_PROXY": "http://proxy", "API_TIMEOUT_MS": "60000",
                   "ANTHROPIC_MODEL": "opus"}


# -- finding claude ----------------------------------------------------------------------


def test_find_claude_prefers_native_exe(tmp_path):
    lookup = platform_paths.find_claude(which=lambda n: "C:\\x\\claude.exe",
                                        native_candidates=[])
    assert lookup.path == "C:\\x\\claude.exe"


@pytest.mark.parametrize("script", ["C:\\npm\\claude.CMD", "C:\\npm\\claude.bat",
                                    "C:\\npm\\claude.ps1"])
def test_find_claude_refuses_scripts(script, tmp_path):
    lookup = platform_paths.find_claude(which=lambda n: script, native_candidates=[])
    assert lookup.path is None and "native" in lookup.problem
    native = tmp_path / "claude.exe"
    native.write_bytes(b"")
    lookup = platform_paths.find_claude(which=lambda n: script, native_candidates=[native])
    assert lookup.path == str(native)


def test_find_claude_missing():
    lookup = platform_paths.find_claude(which=lambda n: None, native_candidates=[])
    assert lookup.path is None and "wasn't found" in lookup.problem


# -- stream-json events ---------------------------------------------------------------


def ev(**data):
    return json.dumps(data)


def test_stream_parser_happy_path():
    parser = StreamParser()
    events = []
    for line in [
        ev(type="system", subtype="session_title_changed", title="t", session_id="s1"),
        ev(type="system", subtype="init", session_id="s1", apiKeySource="none",
           permissionMode="auto", tools=[]),
        ev(type="assistant", session_id="s1", parent_tool_use_id=None,
           message={"content": [{"type": "thinking", "thinking": ""}]}),
        ev(type="assistant", session_id="s1", parent_tool_use_id=None,
           message={"content": [{"type": "text", "text": "Working on it."}]}),
        ev(type="assistant", session_id="s1", parent_tool_use_id=None,
           message={"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}),
        ev(type="assistant", session_id="s1", parent_tool_use_id="toolu_sub",
           message={"content": [{"type": "text", "text": "subagent chatter"}]}),
        ev(type="rate_limit_event", rate_limit_info={}),
        ev(type="result", subtype="success", is_error=False, result="pong",
           session_id="s1", permission_denials=[]),
    ]:
        events.extend(parser.feed(line))
    assert [(e.kind, e.text) for e in events] == [
        ("started", "auto"), ("text", "Working on it."), ("tool", "Bash"),
        ("finished", "pong")]
    assert parser.session_id == "s1" and parser.api_key_source == "none"
    assert not events[-1].is_error and parser.finished


def test_stream_parser_permission_denials():
    parser = StreamParser()
    denied = parser.feed(ev(type="system", subtype="permission_denied", tool_name="Write",
                            message="Claude requested permissions to write to x.txt"))
    assert denied[0].kind == "denied"
    assert denied[0].text == "Write: Claude requested permissions to write to x.txt"
    result = parser.feed(ev(type="result", subtype="success", is_error=False, result="Done",
                            permission_denials=[
                                {"tool_name": "Write", "tool_use_id": "t",
                                 "tool_input": {"file_path": "C:/x/probe.txt"}},
                                {"tool_name": "Bash", "tool_input": {"command": "rm -rf  /"}},
                                {"tool_name": "WebFetch"}, "junk"]))
    assert result[0].denials == ["Write was refused: C:/x/probe.txt",
                                 "Bash was refused: rm -rf /",
                                 "WebFetch was refused", "A tool was refused."]


def test_stream_parser_error_results():
    parser = StreamParser()
    err = parser.feed(ev(type="result", subtype="error_max_turns", is_error=True))[0]
    assert err.is_error and "error_max_turns" in err.text
    err2 = StreamParser().feed(ev(type="result", subtype="error_during_execution",
                                  errors=["boom", "bang"]))[0]
    assert err2.is_error and err2.text == "boom; bang"


def test_stream_parser_tolerates_garbage():
    parser = StreamParser()
    assert parser.feed("not json") == []
    assert parser.feed("[1]") == []
    assert parser.feed("") == []
    assert parser.feed(ev(type="assistant", message="odd")) == []
    assert parser.feed(ev(type="brand_new_event", x=1)) == []
    assert parser.bad_lines == 2


@pytest.mark.parametrize("source,problem", [
    ("none", False), (None, False), ("", False),
    ("ANTHROPIC_API_KEY", True), ("apiKeyHelper", True)])
def test_api_key_problem(source, problem):
    assert (cli.api_key_problem(source) is not None) is problem


# -- TurnRunner with a fake process -------------------------------------------------------


class FakeProcess:
    """Byte pipes, like the real Popen the runner makes."""

    def __init__(self, stdout_lines, returncode=0, stderr_lines=()):
        self.stdout = io.BytesIO("".join(x + "\n" for x in stdout_lines).encode("utf-8"))
        self.stderr = io.BytesIO("".join(x + "\n" for x in stderr_lines).encode("utf-8"))
        self.stdin = io.BytesIO()
        self.pid = None
        self.returncode = None
        self._final = returncode
        self.killed = False
        self.written = None
        original_close = self.stdin.close

        def close():
            self.written = self.stdin.getvalue()
            original_close()
        self.stdin.close = close

    def poll(self):
        return self.returncode

    def wait(self):
        self.returncode = -9 if self.killed else self._final
        return self.returncode

    def kill(self):
        self.killed = True


def run_turn(process, tmp_path, command=None, prompt="Hello -p --bare"):
    captured = {}
    events = []
    done = threading.Event()

    def popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured.update(kwargs)
        return process

    def on_event(event):
        events.append(event)
        if event.kind in ("finished", "failed"):
            done.set()

    runner = TurnRunner(command or ["claude", "-p"], str(tmp_path), prompt,
                        on_event, popen=popen, env={"PATH": "x"})
    runner.start()
    assert done.wait(5)
    runner.join(5)
    return runner, events, captured


def test_runner_sends_prompt_on_stdin_and_reports_events(tmp_path):
    process = FakeProcess([
        ev(type="system", subtype="init", session_id="s1", apiKeySource="none"),
        ev(type="assistant", message={"content": [{"type": "text", "text": "pong"}]}),
        ev(type="result", subtype="success", result="pong", session_id="s1"),
    ])
    runner, events, captured = run_turn(process, tmp_path)
    sent = [json.loads(line) for line in process.written.decode("utf-8").splitlines()]
    assert sent[0]["type"] == "control_request"
    assert sent[0]["request"]["subtype"] == "initialize"
    assert sent[1]["type"] == "user"
    assert sent[1]["message"] == {"role": "user", "content": "Hello -p --bare"}
    assert captured["cwd"] == str(tmp_path)
    assert captured["env"] == {"PATH": "x"}
    assert "encoding" not in captured and "text" not in captured  # byte pipes
    assert [e.kind for e in events] == ["started", "text", "finished"]
    assert events[-1].session_id == "s1"
    assert runner.session_started


def test_runner_stops_when_an_api_key_would_be_billed(tmp_path):
    process = FakeProcess([
        ev(type="system", subtype="init", session_id="s1", apiKeySource="ANTHROPIC_API_KEY"),
        ev(type="assistant", message={"content": [{"type": "text", "text": "billed!"}]}),
        ev(type="result", subtype="success", result="billed!"),
    ])
    _runner, events, _ = run_turn(process, tmp_path)
    assert process.killed
    assert [e.kind for e in events] == ["failed"]
    assert "API key" in events[0].text


@pytest.mark.parametrize("command,stopped", [
    (["claude", "-p"], True),                          # Claude Code's default
    (["claude", "-p", "--model", "opus"], True),       # a fallback to Fable
    (["claude", "-p", "--model", "claude-fable-5-1"], False),  # chosen
])
def test_runner_stops_a_turn_on_an_unchosen_fable(tmp_path, command, stopped):
    process = FakeProcess([
        ev(type="system", subtype="init", session_id="s1", apiKeySource="none",
           model="claude-fable-5-1"),
        ev(type="assistant", message={"content": [{"type": "text", "text": "hi"}]}),
        ev(type="result", subtype="success", result="hi"),
    ])
    _runner, events, _ = run_turn(process, tmp_path, command=command)
    if stopped:
        assert process.killed
        assert [e.kind for e in events] == ["failed"]
        assert "Fable" in events[0].text and "Change Model" in events[0].text
    else:
        assert events[-1].kind == "finished"


def test_runner_reports_exit_without_result(tmp_path):
    process = FakeProcess([], returncode=1, stderr_lines=["Error: not logged in"])
    runner, events, _ = run_turn(process, tmp_path)
    assert [e.kind for e in events] == ["failed"]
    assert "exit code 1" in events[0].text and "not logged in" in events[0].text
    assert not runner.session_started


def test_runner_missing_folder(tmp_path):
    events = []
    done = threading.Event()
    runner = TurnRunner(["claude"], str(tmp_path / "gone"), "hi",
                        lambda e: (events.append(e), done.set()),
                        popen=lambda *a, **k: pytest.fail("must not start"), env={})
    runner.start()
    assert done.wait(5)
    assert events[0].kind == "failed" and "doesn't exist" in events[0].text


def test_runner_claude_not_found(tmp_path):
    events = []
    done = threading.Event()

    def popen(*a, **k):
        raise FileNotFoundError("claude not found")
    runner = TurnRunner(["claude"], str(tmp_path), "hi",
                        lambda e: (events.append(e), done.set()), popen=popen, env={})
    runner.start()
    assert done.wait(5)
    assert events[0].kind == "failed"


def test_runner_cancel(tmp_path):
    process = FakeProcess([])
    runner = TurnRunner(["claude"], str(tmp_path), "hi", lambda e: None,
                        popen=lambda *a, **k: process, env={})
    runner._process = process
    runner.cancel()
    assert process.killed


def test_cancel_during_popen_kills_at_once(tmp_path):
    """cancel() landing while Popen is still starting the process."""
    process = FakeProcess([])
    events = []
    done = threading.Event()
    holder = {}

    def popen(*a, **k):
        holder["runner"].cancel()  # arrives mid-start, before _process is set
        return process
    runner = TurnRunner(["claude"], str(tmp_path), "hi",
                        lambda e: (events.append(e), done.set()), popen=popen, env={})
    holder["runner"] = runner
    runner.start()
    assert done.wait(5)
    assert process.killed
    assert events[-1].kind == "failed" and events[-1].text == "Stopped."


def test_cancel_before_start_never_launches(tmp_path):
    events = []
    done = threading.Event()
    runner = TurnRunner(["claude"], str(tmp_path), "hi",
                        lambda e: (events.append(e), done.set()),
                        popen=lambda *a, **k: pytest.fail("must not start"), env={})
    runner.cancel()
    runner.start()
    assert done.wait(5)
    assert events[0].text == "Stopped."


def test_runner_survives_a_broken_callback(tmp_path):
    process = FakeProcess([ev(type="result", subtype="success", result="ok")])
    calls = []

    def on_event(event):
        calls.append(event.kind)
        raise RuntimeError("UI bug")
    runner = TurnRunner(["claude"], str(tmp_path), "hi", on_event,
                        popen=lambda *a, **k: process, env={})
    runner.start()
    runner.join(5)
    assert calls == ["finished"]


def test_runner_tracks_activity_and_elapsed(tmp_path):
    times = iter([100.0, 165.0])
    process = FakeProcess([
        ev(type="system", subtype="init", session_id="s1", apiKeySource="none"),
        ev(type="assistant", message={"content": [{"type": "tool_use", "name": "Bash"}]}),
        ev(type="result", subtype="success", result="ok"),
    ])
    runner = TurnRunner(["claude"], str(tmp_path), "hi", lambda e: None,
                        popen=lambda *a, **k: process, env={}, clock=lambda: next(times))
    runner.start()
    runner.join(5)
    assert runner.session_started and runner.last_activity == "using Bash"
    assert runner.elapsed() == 65.0


@pytest.mark.parametrize("seconds,words", [
    (0, "0 seconds"), (1, "1 second"), (65, "1 minute 5 seconds"), (120, "2 minutes"),
    (3600, "1 hour"), (3725, "1 hour 2 minutes")])
def test_describe_elapsed(seconds, words):
    assert cli.describe_elapsed(seconds) == words


def test_permission_modes_offered():
    assert cli.PERMISSION_MODE_VALUES == ["auto", "acceptEdits", "manual", "plan"]
    assert cli.DEFAULT_PERMISSION_MODE == "auto"


# -- a real child process ---------------------------------------------------------------------

FAKE_CLAUDE = Path(__file__).with_name("fake_claude.py")


def wait_for_pid_file(path, timeout=20.0):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return int(path.read_text().strip())
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError(f"{path} never appeared")


def run_real(tmp_path, prompt, mode="normal", cancel_when_started=False):
    log = tmp_path / "fake.log"
    env = {**child_environment(), "FAKE_CLAUDE_LOG": str(log), "FAKE_CLAUDE_MODE": mode,
           "CLAUDECODE": "1"}
    env = child_environment(env)
    events = []
    done = threading.Event()

    def on_event(event):
        events.append(event)
        if event.kind in ("finished", "failed"):
            done.set()
    runner = TurnRunner([sys.executable, str(FAKE_CLAUDE), "--session-id", "abc-1"],
                        str(tmp_path), prompt, on_event, env=env)
    runner.start()
    if cancel_when_started:
        # Cancel only once the grandchild really exists.
        wait_for_pid_file(tmp_path / "grandchild.pid")
        runner.cancel()
    assert done.wait(30)
    runner.join(10)
    return events, (json.loads(log.read_text(encoding="utf-8")) if log.exists() else None)


def test_real_child_process_pipes_bytes_exactly(tmp_path):
    prompt = "line one\nline two \u2014 caf\u00e9 \u2028 end"
    events, seen = run_real(tmp_path, prompt)
    assert seen["prompt"] == prompt          # no CRLF, no mangled UTF-8
    assert seen["claude_env"] == []           # CLAUDECODE was stripped
    kinds = [e.kind for e in events]
    assert kinds == ["started", "text", "finished"]
    assert seen["received"] == ["control_request", "user"]
    # The reply carries a raw U+2028 inside the JSON line; it must survive.
    assert events[1].text == "reply\u2028with a line separator"
    assert events[-1].text == "done"


def test_real_child_process_cancel_kills_the_tree(tmp_path):
    events, seen = run_real(tmp_path, "wait", mode="hang", cancel_when_started=True)
    assert events[-1].kind == "failed" and events[-1].text == "Stopped."
    grandchild = int((tmp_path / "grandchild.pid").read_text())
    import time
    deadline = time.time() + 5
    while platform_paths.pid_alive(grandchild) and time.time() < deadline:
        time.sleep(0.1)
    assert not platform_paths.pid_alive(grandchild)


def test_real_child_process_permission_request_answered(tmp_path):
    log = tmp_path / "fake.log"
    env = child_environment({**child_environment(), "FAKE_CLAUDE_LOG": str(log),
                             "FAKE_CLAUDE_MODE": "ask"})
    events = []
    done = threading.Event()
    holder = {}

    def on_event(event):
        events.append(event)
        if event.kind == "permission":
            # The UI answers from its own thread.
            threading.Thread(target=lambda: holder["runner"].respond(
                event.request.request_id, cli.deny_response("not today"))).start()
        if event.kind in ("finished", "failed"):
            done.set()
    runner = TurnRunner([sys.executable, str(FAKE_CLAUDE)], str(tmp_path), "push it",
                        on_event, env=env)
    holder["runner"] = runner
    runner.start()
    assert done.wait(30)
    runner.join(10)
    kinds = [e.kind for e in events]
    assert kinds == ["started", "permission", "text", "finished"]
    request = events[1].request
    assert request.tool_name == "Bash" and request.summary() == "Claude wants to run git push"
    assert events[-1].text == "deny"
    answer = json.loads(log.read_text(encoding="utf-8"))["answer"]
    assert answer == {"type": "control_response", "response": {
        "subtype": "success", "request_id": "req-1",
        "response": {"behavior": "deny", "message": "not today"}}}
    assert runner.pending == {}
    assert not runner.respond("req-1", cli.deny_response())  # already answered


# -- permission requests -----------------------------------------------------------------


def control(request_id="r1", **request):
    return ev(type="control_request", request_id=request_id,
              request={"subtype": "can_use_tool", **request})


def test_parser_turns_can_use_tool_into_a_permission_event():
    parser = StreamParser()
    events = parser.feed(control(
        tool_name="PowerShell", input={"command": "npm init -y", "description": "Init"},
        description="Initialize a new npm project",
        permission_suggestions=[{"type": "addRules", "behavior": "allow",
                                 "destination": "localSettings",
                                 "rules": [{"toolName": "PowerShell",
                                            "ruleContent": "npm init -y"}]}],
        tool_use_id="t1"))
    assert [e.kind for e in events] == ["permission"]
    request = events[0].request
    assert request.request_id == "r1"
    assert request.summary() == "Claude wants to run npm init -y"
    assert "PowerShell command:\nnpm init -y" in request.detail()
    assert "Why: Initialize a new npm project" in request.detail()
    assert request.session_rules() == ["PowerShell(npm init -y)"]
    assert request.allow_for_session_label() == (
        "Allow, and don't ask again this session for PowerShell(npm init -y)")


def test_parser_refuses_other_control_requests_and_reads_commands():
    parser = StreamParser()
    assert parser.feed(ev(type="control_request", request_id="h1",
                          request={"subtype": "hook_callback"})) == []
    assert parser.unsupported_requests == ["h1"]
    parser.feed(ev(type="control_response", response={
        "subtype": "success", "request_id": cli.INIT_REQUEST_ID,
        "response": {"commands": [{"name": "compact", "description": "Compact"}, "junk"]}}))
    assert parser.commands == [{"name": "compact", "description": "Compact"}]


@windows_paths
def test_allow_responses():
    request = cli.PermissionRequest("r1", "Write", {"file_path": "C:\\x\\a.txt", "content": "hi"},
                                    suggestions=[{"type": "setMode", "mode": "acceptEdits",
                                                  "destination": "session"}])
    assert request.summary() == "Claude wants to write a.txt"
    assert cli.allow_response(request) == {"behavior": "allow", "updatedInput": request.input}
    assert request.allow_for_session_label().startswith("Allow, and accept all file edits")
    assert cli.allow_response(request, for_session=True)["updatedPermissions"] == [
        {"type": "setMode", "mode": "acceptEdits", "destination": "session"}]
    bash = cli.PermissionRequest("r2", "Bash", {"command": "git push"}, suggestions=[
        {"type": "addRules", "behavior": "allow", "destination": "localSettings",
         "rules": [{"toolName": "Bash", "ruleContent": "git push:*"}]}])
    # Always "session": The Chat Place never writes Claude Code's settings files.
    assert cli.allow_response(bash, for_session=True)["updatedPermissions"] == [
        {"type": "addRules", "rules": [{"toolName": "Bash", "ruleContent": "git push:*"}],
         "behavior": "allow", "destination": "session"}]
    plain = cli.PermissionRequest("r3", "WebFetch", {"url": "https://example.com"})
    assert plain.allow_for_session_label() == ""
    assert "updatedPermissions" not in cli.allow_response(plain, for_session=True)


def test_plan_approval_switches_mode_and_deny_carries_the_reason():
    plan = cli.PermissionRequest("r4", "ExitPlanMode", {"plan": "# Plan\n1. Do it"})
    assert plan.is_plan and plan.plan() == "# Plan\n1. Do it"
    assert plan.summary() == "Claude's plan is ready for you to approve"
    assert cli.allow_response(plan, mode="acceptEdits")["updatedPermissions"] == [
        {"type": "setMode", "mode": "acceptEdits", "destination": "session"}]
    assert cli.deny_response("Keep it smaller") == {"behavior": "deny",
                                                    "message": "Keep it smaller"}
    assert cli.deny_response("  ")["message"]  # never empty


def test_questions_answered_through_updated_input():
    questions = [{"question": "Which color?", "header": "Color", "multiSelect": False,
                  "options": [{"label": "Red", "description": "Warm"},
                              {"label": "Blue", "description": "Cool"}]},
                 {"question": "Which size?", "options": [{"label": "S"}]}]
    request = cli.PermissionRequest("r5", "AskUserQuestion", {"questions": questions})
    assert request.is_question
    assert request.summary() == "Claude asks: Which color? (and 1 more)"
    response = cli.answer_questions_response(request, {"Which color?": "Blue",
                                                       "Which size?": "S"})
    assert response == {"behavior": "allow", "updatedInput": {
        "questions": questions, "answers": {"Which color?": "Blue", "Which size?": "S"}}}


def test_allowed_tools_go_on_every_turn_and_unsafe_rules_are_dropped():
    rules = ["Bash(git push:*)", "Edit", "--dangerously-skip-permissions", "Bash(a\nb)"]
    for command in (build_new_command(EXE, "aaaa-1111", "t", "auto", allowed_tools=rules),
                    build_resume_command(EXE, "aaaa-1111", "auto", OWN, DESKTOP,
                                         allowed_tools=rules)):
        at = command.index("--allowedTools")
        assert command[at + 1: at + 3] == ["Bash(git push:*)", "Edit"]
        assert command[at + 3].startswith("--")  # the list ends at the next flag
        assert "--dangerously-skip-permissions" not in command
    assert "--allowedTools" not in build_new_command(EXE, "aaaa-1111", "t", "auto")


@pytest.mark.parametrize("name,tool_input,words", [
    ("Bash", {"command": "git  status"}, "run git status"),
    pytest.param("Edit", {"file_path": "C:\\r\\main.py"}, "edit main.py",
                 marks=windows_paths),
    ("WebFetch", {"url": "https://x.org"}, "fetch https://x.org"),
    ("WebSearch", {"query": "wx accessible"}, "search the web for wx accessible"),
    ("Task", {}, "use Task"),
    ("mcp__x__y", {"pattern": "*.py"}, "use mcp__x__y: *.py"),
])
def test_describe_tool_use(name, tool_input, words):
    assert cli.describe_tool_use(name, tool_input) == words


# -- continuing another session as a copy (#189) -------------------------------------------


def test_fork_command_reads_the_source_and_writes_a_new_session():
    command = cli.build_fork_command(EXE, "dddd-2222", "nnnn-3333", " Carry  on ", "auto",
                                     "sonnet", taken_ids=OWN | DESKTOP)
    assert command[command.index("--resume") + 1] == "dddd-2222"
    assert "--fork-session" in command
    assert command[command.index("--session-id") + 1] == "nnnn-3333"
    assert command[command.index("--name") + 1] == "Carry on"
    assert command[command.index("--model") + 1] == "sonnet"


@pytest.mark.parametrize("source,new", [
    ("local_abc", "nnnn-3333"),       # a desktop app id, not a Claude Code one
    ("-p", "nnnn-3333"),
    ("dddd-2222", "dddd-2222"),       # the copy needs its own id
    ("dddd-2222", "aaaa-1111"),       # already taken
    ("dddd-2222", "--resume"),
])
def test_fork_command_refuses_bad_ids(source, new):
    with pytest.raises(ValueError):
        cli.build_fork_command(EXE, source, new, "t", "auto", taken_ids=OWN)


def test_tool_events_say_what_the_tool_acts_on():
    parser = StreamParser()
    events = parser.feed(ev(type="assistant", message={"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "git  status"}},
        {"type": "tool_use", "name": "Task", "input": {}}]}))
    assert [(e.text, e.detail) for e in events] == [("Bash", "Bash: git status"),
                                                    ("Task", "Task")]


# -- slash commands and skills (#23) --------------------------------------------------------


def test_usable_commands_puts_yours_first_and_hides_internal_ones():
    commands = [{"name": "compact", "builtin": True}, {"name": "zeta"}, {"name": "__remote"},
                {"name": "Alpha"}, {"description": "no name"}, "junk", {"name": ""}]
    assert [c["name"] for c in cli.usable_commands(commands)] == ["Alpha", "zeta", "compact"]


def test_fetch_commands_asks_only_for_initialize_and_closes(tmp_path):
    answer = ev(type="control_response", response={
        "subtype": "success", "request_id": cli.INIT_REQUEST_ID,
        "response": {"commands": [{"name": "context", "builtin": True}, {"name": "mine"}]}})
    process = FakeProcess([answer])
    seen = {}

    def popen(command, **kwargs):
        seen["command"] = command
        seen.update(kwargs)
        return process
    commands = cli.fetch_commands("claude.exe", str(tmp_path), popen=popen)
    assert [c["name"] for c in commands] == ["mine", "context"]
    assert "--resume" not in seen["command"] and "--session-id" not in seen["command"]
    sent = [json.loads(line) for line in process.written.decode("utf-8").splitlines()]
    assert [m["type"] for m in sent] == ["control_request"]  # no user message: no turn
    assert seen["cwd"] == str(tmp_path)


def test_fetch_commands_gives_nothing_for_a_missing_folder_or_no_answer(tmp_path):
    assert cli.fetch_commands("claude.exe", str(tmp_path / "gone"),
                              popen=lambda *a, **k: pytest.fail("must not start")) == []
    assert cli.fetch_commands("claude.exe", str(tmp_path),
                              popen=lambda *a, **k: FakeProcess([])) == []


def test_init_reports_the_model_in_use():
    from thechatplace.claude_cli import model_matches
    parser = StreamParser()
    events = parser.feed(ev(type="system", subtype="init", session_id="s1",
                            apiKeySource="none", model="claude-sonnet-5-5"))
    assert events[0].kind == "started" and events[0].data == {"model": "claude-sonnet-5-5"}
    assert model_matches("sonnet", "claude-sonnet-5-5")
    assert not model_matches("opus", "claude-sonnet-5-5")
    assert model_matches("", "claude-fable-5-1") and model_matches("opus", "")
    assert model_matches("claude-opus-5-5", "claude-opus-5-5")
    assert model_matches("claude-opus-5-5", "claude-opus-5-5-20261001")
    assert not model_matches("claude-opus-5", "claude-opus-55")
    assert model_matches("claude-opus-5-5", "claude-opus-5-5[1m]")
    # No model, or not a string: nothing to compare.
    for model in (None, 5):
        event = StreamParser().feed(ev(type="system", subtype="init", session_id="s1",
                                       apiKeySource="none", model=model))[0]
        assert event.data == {"model": ""}


def test_model_ids_as_words():
    from thechatplace.claude_cli import model_spoken
    assert model_spoken("claude-sonnet-5-5") == "Sonnet 5.5"
    assert model_spoken("claude-haiku-4-5-20251001") == "Haiku 4.5"
    assert model_spoken("claude-opus-5-5[1m]") == "Opus 5.5"
    assert model_spoken("something-else") == "something-else"


def test_a_turn_on_an_unchosen_fable_is_stopped():
    from thechatplace.claude_cli import chosen_model, fable_problem
    assert chosen_model(["claude", "-p", "--model", "opus"]) == "opus"
    assert chosen_model(["claude", "-p"]) == ""
    assert fable_problem("claude-fable-5-1", "") == (
        "Claude Code would have used Fable, Claude Code's default model. Some plans bill Fable "
        "to usage credits, so The Chat Place didn't send your message. Choose another model "
        "with Session, Change Model, then send again.")
    assert "instead of Opus, the model this session chose" in fable_problem(
        "claude-fable-5-1", "opus")
    assert "as soon as it started" in fable_problem("claude-fable-5-1", "", sent=True)
    assert fable_problem("claude-fable-5-1", "opus")  # a fallback to Fable: stopped too
    assert fable_problem("claude-fable-5-1", "claude-fable-5-1") is None  # chosen
    assert fable_problem("claude-opus-5-5", "") is None
    assert fable_problem("", "") is None


def test_the_message_waits_for_initialize_and_is_never_sent_to_a_fable_default(tmp_path):
    from thechatplace.claude_cli import INIT_REQUEST_ID
    answer = ev(type="control_response", response={
        "subtype": "success", "request_id": INIT_REQUEST_ID,
        "response": {"commands": [], "models": [
            {"value": "default", "resolvedModel": "claude-fable-5-1"},
            {"value": "opus", "resolvedModel": "claude-opus-5-5"}]}})
    process = FakeProcess([answer, ev(type="system", subtype="init", session_id="s1",
                                      apiKeySource="none", model="claude-fable-5-1")])
    runner, events, _ = run_turn(process, tmp_path)
    assert process.killed and runner.stopped_before_answer
    assert [e.kind for e in events] == ["failed"]
    assert "didn't send your message" in events[0].text
    assert b'"type": "user"' not in process.written  # the message never went
    # Opus chosen: initialize answered, then the message goes.
    process = FakeProcess([answer, ev(type="system", subtype="init", session_id="s1",
                                      apiKeySource="none", model="claude-opus-5-5"),
                           ev(type="result", subtype="success", result="ok")])
    _runner, events, _ = run_turn(process, tmp_path, command=["claude", "-p", "--model", "opus"])
    assert events[-1].kind == "finished"
    assert b'"type": "user"' in process.written


def test_an_old_claude_code_is_told_to_update():
    # Claude Code 2.1.258 on a Mac, which predates --permission-prompts.
    text = cli.exit_message(1, "error: unknown option '--permission-prompts'")
    assert text.startswith("Claude Code is too old for The Chat Place")
    assert "--permission-prompts" in text and "claude update" in text
    assert cli.exit_message(3, "boom") == \
        "Claude exited without finishing the turn (exit code 3). boom"
    assert cli.exit_message(3, "") == "Claude exited without finishing the turn (exit code 3)."
