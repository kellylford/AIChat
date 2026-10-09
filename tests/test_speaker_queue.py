"""The speaker queues utterances and stops all of them on an interruption."""
import json
import sys
import threading
import time

import pytest

from thechatplace import speech
from thechatplace.speech import Speaker, SpeechSettings


class FakeEngine:
    """An engine process that 'speaks' until released or killed."""

    started = []

    def __init__(self, command, **kwargs):
        self.command = command
        self.config = json.loads(open(command[command.index("-ConfigPath") + 1]
                                      if "-ConfigPath" in command
                                      else command[command.index("--config") + 1],
                                      encoding="utf-8").read())
        self.done = threading.Event()
        # Set once the speaker is blocked waiting for this engine to finish,
        # so a test knows the speaker has recorded it as running and cannot
        # start the next utterance, without guessing with a sleep (#113).
        self.waiting = threading.Event()
        self.killed = False
        FakeEngine.started.append(self)

    def poll(self):
        return 0 if self.done.is_set() else None

    def wait(self, timeout=None):
        self.waiting.set()
        if not self.done.wait(timeout):
            raise TimeoutError
        return 0

    def kill(self):
        self.killed = True
        self.done.set()


def wait_until(condition, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def text_of(engine):
    return open(engine.command[engine.command.index("-Path") + 1],
                encoding="utf-8").read()


def make(tmp_path, monkeypatch):
    FakeEngine.started = []
    monkeypatch.setattr(speech.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(Speaker, "_command",
                        lambda self, t, c: ["engine", "-Path", str(t), "-ConfigPath", str(c)])
    return Speaker(popen=FakeEngine)


def test_confirmations_queue_instead_of_overlapping(tmp_path, monkeypatch):
    s = make(tmp_path, monkeypatch)
    settings = SpeechSettings()
    assert s.speak("first", settings, interrupt=False)
    assert s.speak("second", settings, interrupt=False)
    assert wait_until(lambda: len(FakeEngine.started) == 1)
    first = FakeEngine.started[0]
    assert first.waiting.wait(5)                 # the speaker is waiting on it
    # Second waits for the first. A short look for a second engine can only
    # catch more, never flake: with a correct speaker none can appear.
    assert not wait_until(lambda: len(FakeEngine.started) > 1, timeout=0.1)
    assert first.config["interrupt"] is False
    assert text_of(first) == "first"
    first.done.set()
    assert wait_until(lambda: len(FakeEngine.started) == 2)
    second = FakeEngine.started[1]
    assert text_of(second) == "second"
    second.done.set()
    assert wait_until(lambda: not s.busy())


def test_utterances_in_one_clock_tick_keep_their_own_files(tmp_path, monkeypatch):
    """On Windows time.time_ns() ticks every 15.6 ms, so file names built from
    it alone collided and the second utterance overwrote the first's text (#113)."""
    monkeypatch.setattr(speech.time, "time_ns", lambda: 1_000_000)
    s = make(tmp_path, monkeypatch)
    settings = SpeechSettings()
    s.speak("first", settings, interrupt=False)
    s.speak("second", settings, interrupt=False)
    assert wait_until(lambda: len(FakeEngine.started) == 1)
    first = FakeEngine.started[0]
    assert first.waiting.wait(5)
    assert text_of(first) == "first"
    first.done.set()
    assert wait_until(lambda: len(FakeEngine.started) == 2)
    second = FakeEngine.started[1]
    assert text_of(second) == "second"
    assert second.command != first.command
    second.done.set()
    assert wait_until(lambda: not s.busy())


def test_an_announcement_stops_everything_in_flight_and_queued(tmp_path, monkeypatch):
    s = make(tmp_path, monkeypatch)
    settings = SpeechSettings()
    s.speak("confirmation one", settings, interrupt=False)
    s.speak("confirmation two", settings, interrupt=False)
    assert wait_until(lambda: len(FakeEngine.started) == 1)
    first = FakeEngine.started[0]
    assert first.waiting.wait(5)                 # it is running, not starting
    s.speak("Session replied", settings, interrupt=True)
    assert first.killed                           # in-flight speech stopped
    assert wait_until(lambda: len(FakeEngine.started) == 2)
    announcement = FakeEngine.started[1]
    assert announcement.config["interrupt"] is True
    text_file = announcement.command[announcement.command.index("-Path") + 1]
    assert open(text_file, encoding="utf-8").read() == "Session replied"
    announcement.done.set()
    assert wait_until(lambda: not s.busy())
    assert len(FakeEngine.started) == 2           # the queued confirmation was dropped


def test_stop_kills_every_running_engine(tmp_path, monkeypatch):
    s = make(tmp_path, monkeypatch)
    s.speak("one", SpeechSettings(), interrupt=False)
    assert wait_until(lambda: len(FakeEngine.started) == 1)
    assert FakeEngine.started[0].waiting.wait(5)
    s.stop()
    assert FakeEngine.started[0].killed
    assert wait_until(lambda: not s.busy())


def test_empty_text_is_not_spoken(tmp_path, monkeypatch):
    s = make(tmp_path, monkeypatch)
    assert s.speak("   ", SpeechSettings()) is False
    assert FakeEngine.started == []


def test_every_utterance_is_logged_in_its_own_file(tmp_path, monkeypatch):
    s = make(tmp_path, monkeypatch)
    s.speak("Sent. Hub is working.", SpeechSettings(), interrupt=False)
    s.speak("Hub replied. " + "word " * 40, SpeechSettings(engine="jaws"))
    lines = (tmp_path / "thechatplace-speak" / "speech.log").read_text(
        encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0].endswith(" queue auto 21 chars: Sent. Hub is working.")
    assert " interrupt jaws " in lines[1] and lines[1].endswith("…")
    assert len(lines[1].split("chars: ", 1)[1]) == 80
    s.stop()


def test_speech_log_drops_its_older_half_when_too_big(tmp_path, monkeypatch):
    monkeypatch.setattr(speech, "LOG_LIMIT", 1000)
    s = make(tmp_path, monkeypatch)
    for i in range(60):
        s.speak(f"utterance {i}", SpeechSettings(), interrupt=False)
    text = (tmp_path / "thechatplace-speak" / "speech.log").read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) < 1100
    assert text.splitlines()[-1].endswith("utterance 59")
    assert text.splitlines()[0][:4].isdigit()  # starts on a whole line
    s.stop()


@pytest.mark.skipif(sys.platform == "win32", reason="process groups are POSIX")
def test_stopping_speech_also_stops_what_the_script_started(tmp_path):
    """speak-engine.sh runs osascript as a child, so it can fall back to say
    when VoiceOver refuses. Killing only the script left osascript running
    to hand VoiceOver stale text after a newer announcement."""
    import os
    import subprocess
    import time
    from thechatplace.speech import _kill_quietly

    pid_file = tmp_path / "child.pid"
    script = f"sleep 30 & echo $! > {pid_file}; wait"
    process = subprocess.Popen(["/bin/bash", "-c", script], start_new_session=True)
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text().strip():
            break
        time.sleep(0.02)
    child = int(pid_file.read_text())
    _kill_quietly(process)
    process.wait(timeout=5)
    for _ in range(100):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        pytest.fail("the script's child outlived it")
