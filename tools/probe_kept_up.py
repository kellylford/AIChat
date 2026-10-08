"""Probe for #123: does a kept-up ``claude -p`` stream-json session with Remote
Control run a turn when another session messages it?

Starts one session the way The Chat Place does (same flags, same stripped
environment, Remote Control on), sends one short message, and then keeps stdin
open, logging every stdout line with a timestamp to the log file, until the
time runs out. While it runs, message it from another session and watch the log.

    python tools/probe_kept_up.py LOG [SECONDS] [NAME]

PROBE_RESUME=<id> resumes a session instead (PROBE_CWD its folder),
PROBE_NAME_ON_RESUME=1 passes --name on resume too, and PROBE_NO_MESSAGE=1
sends no message: the process only comes online.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from thechatplace import claude_cli, platform_paths  # noqa: E402


def main() -> None:
    log_path = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 600
    name = sys.argv[3] if len(sys.argv) > 3 else "TCP probe 123"
    exe = platform_paths.claude_executable() or "claude"
    resume = os.environ.get("PROBE_RESUME", "")
    sid = resume or claude_cli.new_session_id()
    if resume:
        command = claude_cli.build_resume_command(exe, sid, "manual", {sid}, (), "haiku")
        if os.environ.get("PROBE_NAME_ON_RESUME"):
            command += ["--name", name]
    else:
        command = claude_cli.build_new_command(exe, sid, name, "manual", "haiku")
    env = claude_cli.child_environment()
    env["CLAUDE_CODE_EMIT_SESSION_STATE_EVENTS"] = "1"
    cwd = os.environ.get("PROBE_CWD") or tempfile.mkdtemp(prefix="tcp-probe-")
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    start = time.monotonic()

    def note(kind, text):
        log.write(f"{time.monotonic() - start:8.1f} {kind} {text}\n")

    note("cmd", json.dumps(command))
    note("cwd", cwd)
    proc = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def drain_err():
        for raw in iter(proc.stderr.readline, b""):
            note("ERR", raw.decode("utf-8", "replace").rstrip())
    threading.Thread(target=drain_err, daemon=True).start()

    proc.stdin.write(claude_cli.initialize_line())
    proc.stdin.write(claude_cli.remote_control_line(name))
    if not os.environ.get("PROBE_NO_MESSAGE"):
        proc.stdin.write(claude_cli.message_line("Reply with only the word: ready"))
    proc.stdin.flush()

    def answer_requests(line):
        try:
            event = json.loads(line)
        except ValueError:
            return
        if event.get("type") == "control_request":
            # Refuse anything that asks: the probe approves nothing.
            req = event.get("request") or {}
            body = ({"behavior": "deny", "message": "Probe: nothing is approved."}
                    if req.get("subtype") == "can_use_tool" else None)
            response = ({"subtype": "success", "request_id": event.get("request_id"),
                         "response": body} if body else
                        {"subtype": "error", "request_id": event.get("request_id"),
                         "error": "unsupported"})
            proc.stdin.write((json.dumps({"type": "control_response", "response": response})
                              + "\n").encode())
            proc.stdin.flush()
            note("SENT", json.dumps(response)[:300])

    def reader():
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            note("OUT", line[:4000])
            answer_requests(line)
    threading.Thread(target=reader, daemon=True).start()

    deadline = start + seconds
    while time.monotonic() < deadline and proc.poll() is None:
        time.sleep(1)
    note("end", f"exited={proc.poll()}")
    try:
        proc.stdin.close()
        proc.wait(timeout=30)
    except Exception:  # noqa: BLE001
        proc.kill()
    note("end", f"code={proc.returncode}")


if __name__ == "__main__":
    main()
