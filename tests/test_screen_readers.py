"""Speaking through JAWS and NVDA from the app's own process (#98)."""
import struct

import pytest

from thechatplace import screen_readers
from thechatplace.screen_readers import JawsClient, NvdaClient, Outcome, ScreenReaders

from markers import windows_screen_readers


class FakeClient:
    def __init__(self, problem=None, answers=False):
        self.problem = problem
        self.calls = []
        self._answers = answers

    def answers(self):
        return self._answers

    def speak(self, text, interrupt):
        self.calls.append((text, interrupt))
        return self.problem


def readers(running, nvda=None, jaws=None, locked=False):
    nvda = nvda or FakeClient()
    jaws = jaws or FakeClient()
    return ScreenReaders(nvda=nvda, jaws=jaws, processes=lambda: set(running),
                         locked=lambda: locked), nvda, jaws


def test_no_screen_reader_running_leaves_it_to_a_windows_voice():
    bridge, nvda, jaws = readers({"explorer.exe"})
    outcome = bridge.speak("Hello", "auto", True)
    assert outcome.running == [] and outcome.spoke is None
    assert not outcome.unreachable
    assert nvda.calls == [] and jaws.calls == []
    assert outcome.describe() == "no screen reader running"


def test_nvda_running_speaks_through_nvda():
    bridge, nvda, jaws = readers({"nvda.exe"})
    outcome = bridge.speak("Session replied", "auto", True)
    assert outcome.spoke == "nvda"
    assert nvda.calls == [("Session replied", True)]
    assert jaws.calls == []
    assert outcome.describe() == "spoke through NVDA"


def test_automatic_and_jaws_try_jaws_first_and_nvda_choice_tries_nvda_first():
    for engine, first in (("auto", "jaws"), ("jaws", "jaws"), ("nvda", "nvda")):
        bridge, nvda, jaws = readers({"nvda.exe", "jfw.exe"})
        assert bridge.speak("x", engine, False).spoke == first
        assert (jaws.calls if first == "jaws" else nvda.calls) == [("x", False)]
        assert (nvda.calls if first == "jaws" else jaws.calls) == []


def test_one_failing_screen_reader_falls_to_the_other_running_one():
    bridge, nvda, jaws = readers({"nvda.exe", "jfw.exe"}, jaws=FakeClient("refused the text"))
    outcome = bridge.speak("x", "auto", True)
    assert outcome.spoke == "nvda"
    assert outcome.problems == {"jaws": "refused the text"}


def test_running_but_unreachable_is_reported_not_left_to_a_windows_voice():
    """The #98 bug: NVDA running, the client failing, and a Windows voice
    speaking over NVDA. Now that's an unreachable outcome with a reason."""
    bridge, nvda, _ = readers({"nvda.exe"}, nvda=FakeClient("didn't answer (Windows error 1722)"))
    outcome = bridge.speak("x", "auto", True)
    assert outcome.spoke is None and outcome.unreachable
    assert outcome.describe() == ("not spoken: NVDA is running but didn't answer "
                                  "(Windows error 1722)")


def test_nothing_is_sent_while_windows_is_locked():
    """NV Access: NVDA runs on the lock screen, so don't hand it private text."""
    bridge, nvda, _ = readers({"nvda.exe"}, locked=True)
    outcome = bridge.speak("a private reply", "auto", True)
    assert outcome.locked and not outcome.unreachable and outcome.spoke is None
    assert nvda.calls == []
    assert outcome.describe() == "not spoken: Windows is locked"


def test_an_unknown_engine_is_treated_as_automatic():
    bridge, _, jaws = readers({"jfw.exe"})
    assert bridge.speak("x", "voiceover", True).spoke == "jaws"


class FakeFunction:
    def __init__(self, result, log, name):
        self.result, self.log, self.name = result, log, name
        self.restype = self.argtypes = None

    def __call__(self, *args):
        self.log.append((self.name,) + args)
        return self.result


class FakeDll:
    def __init__(self, running=0, speak=0):
        self.log = []
        self.nvdaController_testIfRunning = FakeFunction(running, self.log, "test")
        self.nvdaController_cancelSpeech = FakeFunction(0, self.log, "cancel")
        self.nvdaController_speakText = FakeFunction(speak, self.log, "speak")


def test_nvda_client_checks_nvda_answers_then_cancels_and_speaks(tmp_path):
    dll_file = tmp_path / "nvdaControllerClient.dll"
    dll_file.write_bytes(b"MZ")
    dll = FakeDll()
    loads = []
    client = NvdaClient(dll_file, loader=lambda path: loads.append(path) or dll)
    assert client.speak("Hi", interrupt=True) is None
    assert dll.log == [("test",), ("cancel",), ("speak", "Hi")]
    dll.log.clear()
    assert client.speak("Queued", interrupt=False) is None
    assert dll.log == [("test",), ("speak", "Queued")]
    assert loads == [str(dll_file)]  # loaded once


def test_nvda_client_reports_why_it_did_not_speak(tmp_path):
    dll_file = tmp_path / "nvdaControllerClient.dll"
    dll_file.write_bytes(b"MZ")
    quiet = NvdaClient(dll_file, loader=lambda path: FakeDll(running=1722))
    assert quiet.speak("x", True) == "didn't answer (Windows error 1722)"
    refusing = NvdaClient(dll_file, loader=lambda path: FakeDll(speak=5))
    assert refusing.speak("x", True) == "refused the text (Windows error 5)"
    missing = NvdaClient(tmp_path / "gone.dll")
    assert "missing" in missing.speak("x", True)


def test_nvda_client_load_error_names_no_path(tmp_path):
    """The reason goes into bug reports, which carry no paths."""
    dll_file = tmp_path / "secret-folder" / "nvdaControllerClient.dll"
    dll_file.parent.mkdir()
    dll_file.write_bytes(b"MZ")

    def refuse(path):
        error = OSError(f"[WinError 193] {path} is not a valid Win32 application")
        error.winerror = 193
        raise error

    problem = NvdaClient(dll_file, loader=refuse).speak("x", True)
    assert problem == "the NVDA controller client couldn't be loaded (error 193)"
    assert "secret-folder" not in problem


def test_jaws_client_says_the_string_with_the_interrupt_flag():
    said = []

    class Api:
        def SayString(self, text, flush):
            said.append((text, flush))
            return True

    assert JawsClient(create=Api).speak("Hello", interrupt=False) is None
    assert said == [("Hello", False)]


def test_jaws_client_reports_refusals_and_a_missing_interface():
    class Refusing:
        def SayString(self, text, flush):
            return False

    def unregistered():
        raise OSError("Invalid class string")

    assert JawsClient(create=Refusing).speak("x", True) == "refused the text"
    assert JawsClient(create=unregistered).speak("x", True).startswith(
        "its speech interface couldn't be reached")


@pytest.mark.parametrize("platform_tag, folder", [
    ("win-amd64", "x64"), ("win-arm64", "arm64"), ("win32", "x64")])
def test_the_client_matches_this_process_not_nvda(monkeypatch, platform_tag, folder):
    monkeypatch.setattr(screen_readers.sysconfig, "get_platform", lambda: platform_tag)
    assert screen_readers.nvda_client_path().parent.name == folder


@pytest.mark.parametrize("folder, machine", [("x64", 0x8664), ("arm64", 0xAA64)])
def test_the_bundled_clients_are_there_and_built_for_their_folder(monkeypatch, folder, machine):
    tag = "win-arm64" if folder == "arm64" else "win-amd64"
    monkeypatch.setattr(screen_readers.sysconfig, "get_platform", lambda: tag)
    data = screen_readers.nvda_client_path().read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe:pe + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", data, pe + 4)[0] == machine
    assert (screen_readers.nvda_client_path().parents[1] / "license.txt").is_file()


@windows_screen_readers
def test_the_real_client_loads_and_answers_for_nvda():
    """The bundled DLL loads in this Python. With NVDA running it speaks a
    blank; without it (CI) it says NVDA didn't answer, never a crash."""
    problem = NvdaClient().speak(" ", interrupt=False)
    assert problem is None or problem.startswith("didn't answer")


def test_outcome_describes_two_running_readers_that_both_failed():
    outcome = Outcome(running=["jaws", "nvda"],
                      problems={"jaws": "refused the text",
                                "nvda": "didn't answer (Windows error 1722)"})
    assert outcome.describe() == ("not spoken: JAWS is running but refused the text; "
                                  "NVDA is running but didn't answer (Windows error 1722)")


def test_nvda_that_answers_counts_as_running_whatever_its_process_is_called():
    """NVDA's folder has other launchers (nvda_uiAccess.exe...); if it
    answers its controller, it's running, so no Windows voice speaks over it."""
    bridge, nvda, _ = readers({"explorer.exe"}, nvda=FakeClient(answers=True))
    outcome = bridge.speak("x", "auto", True)
    assert outcome.spoke == "nvda" and outcome.running == ["nvda"]


def test_nvdas_other_launchers_count_as_nvda_running():
    bridge, _, _ = readers({"nvda_uiaccess.exe"})
    assert bridge.running() == ["nvda"]


def test_error_text_is_a_code_never_a_message():
    class ComError(Exception):
        hresult = -2147221005  # CO_E_CLASSSTRING

    class WinError(OSError):
        winerror = 1722

    assert screen_readers.error_code(ComError(r"C:\Users\someone\secret")) == "error 0x800401F3"
    assert screen_readers.error_code(WinError("x")) == "error 1722"
    assert screen_readers.error_code(ValueError(r"C:\path")) == "ValueError"


@windows_screen_readers
def test_the_process_list_is_this_sessions_and_includes_this_python():
    import os
    import sys
    from thechatplace import platform_paths
    names = platform_paths.running_process_names()
    assert os.path.basename(sys.executable).lower() in names
    assert isinstance(platform_paths.windows_locked(), bool)
