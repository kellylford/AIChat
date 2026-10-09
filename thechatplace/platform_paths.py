"""Everything that knows which operating system it is running on.

The rest of the app asks this module where things live and how to do the
few OS-level things it needs (is a process alive, open a URL with the shell).
A Mac port should only have to touch this file and the speech scripts.

Locations, as found on Windows with Claude Code 2.1 and the Claude desktop
app (none of this is documented, so every caller treats it as best effort):

* Desktop app session metadata:
  ``%APPDATA%\\Claude\\claude-code-sessions\\<id>\\<orgId>\\local_<id>.json``,
  or for the Microsoft Store version
  ``%LOCALAPPDATA%\\Packages\\Claude_<id>\\LocalCache\\Roaming\\Claude\\claude-code-sessions``
* Transcripts: ``%USERPROFILE%\\.claude\\projects\\<encoded cwd>\\<cliSessionId>.jsonl``
* Live sessions: ``%USERPROFILE%\\.claude\\sessions\\<pid>.json``
* The Chat Place's own files: ``%APPDATA%\\TheChatPlace\\``
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional

APP_DIR_NAME = "TheChatPlace"


def claude_home() -> Path:
    """``~/.claude`` (honours CLAUDE_CONFIG_DIR, as Claude Code does)."""
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude"


def projects_dir() -> Path:
    return claude_home() / "projects"


def live_sessions_dir() -> Path:
    return claude_home() / "sessions"


def _roaming_dir() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata)
        return Path.home() / "AppData" / "Roaming"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def desktop_sessions_dir() -> Path:
    """Where the Claude desktop app keeps one JSON file per Code session, when
    it was installed with its own installer."""
    return _roaming_dir() / "Claude" / "claude-code-sessions"


def _store_app_sessions_dirs() -> List[Path]:
    """The same folder for the Microsoft Store (MSIX) version of the desktop
    app (issue #183). Windows redirects a packaged app's AppData writes into
    its package folder, so ``%APPDATA%\\Claude`` doesn't exist there. Matched
    on ``Claude_*`` rather than the package id seen on Kelly's PCs
    (``Claude_pzs8sxrjxfjjc``), in case it differs."""
    if sys.platform != "win32":
        return []
    local = os.environ.get("LOCALAPPDATA")
    packages = Path(local) / "Packages" if local else Path.home() / "AppData" / "Local" / "Packages"
    try:
        return sorted(p / "LocalCache" / "Roaming" / "Claude" / "claude-code-sessions"
                      for p in packages.glob("Claude_*"))
    except OSError:
        return []


def desktop_sessions_dirs() -> List[Path]:
    """Every folder that holds desktop app session files, that exists. Both
    kinds of install can be present (switching from one to the other leaves
    the old folder behind); callers read all of them."""
    candidates = [desktop_sessions_dir(), *_store_app_sessions_dirs()]
    return [path for path in candidates if path.is_dir()]


def app_icon_path() -> Path:
    """The app's icon (#64), shipped with the package (``assets``)."""
    return Path(__file__).resolve().parent / "assets" / "app.ico"


def user_guide_path() -> Path:
    """The user guide's Markdown (#102), shipped in ``assets`` like the icon so
    every build has it; tools/make_docs.py makes the docs/ copies from it."""
    return Path(__file__).resolve().parent / "assets" / "user-guide.md"


def app_data_dir() -> Path:
    """The Chat Place's own settings and session store."""
    return _roaming_dir() / APP_DIR_NAME


def default_projects_root() -> Path:
    """Where the New Session folder picker starts."""
    github = Path.home() / "GitHub"
    return github if github.is_dir() else Path.home()


_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def encode_cwd(cwd: str) -> str:
    """The folder name Claude Code uses for a working directory's transcripts.

    Every character that is not an ASCII letter or digit becomes ``-``, so
    ``C:\\Users\\kelly\\GitHub\\QuickMail`` is ``C--Users-kelly-GitHub-QuickMail``.
    Verified against every transcript on Kelly's PC on 2026-10-06 (87 of 87
    existing transcripts matched; the rest had been deleted by retention).
    """
    return _NON_ALNUM.sub("-", cwd or "")


# Session ids end up in file names, glob patterns and command lines. Refuse
# anything that is not a plain id, so a malformed metadata file cannot point us
# at another file, and an id can never be read as a command-line flag (it must
# not start with "-").
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")


def transcript_path(cwd: str, cli_session_id: str,
                    root: Optional[Path] = None) -> Optional[Path]:
    """Find a session's transcript, or None when it no longer exists.

    The encoded-cwd mapping is tried first; if it misses (a format change, a
    very long path Claude Code shortened), every project folder is searched for
    the session id, which is unique on its own.
    """
    if not cli_session_id or not _SAFE_ID.match(cli_session_id):
        return None
    root = root or projects_dir()
    direct = root / encode_cwd(cwd) / f"{cli_session_id}.jsonl"
    if direct.is_file():
        return direct
    try:
        for candidate in root.glob(f"*/{cli_session_id}.jsonl"):
            if candidate.is_file():
                return candidate
    except OSError:
        pass
    return None




def is_safe_id(value: str) -> bool:
    return bool(value) and bool(_SAFE_ID.match(value))


#: ``process_start`` for a process you may not look at: not one of yours,
#: so not a Claude Code you started (a system service, say).
NOT_YOURS = -1


def process_start(pid: int) -> Optional[int]:
    """When a running process started, as a Windows FILETIME (100 ns since
    1601): what Claude Code writes as ``procStart`` in its pid files.
    ``NOT_YOURS`` when Windows won't say (access denied); None when it can't
    be known (not Windows, no such process)."""
    if sys.platform != "win32" or not isinstance(pid, int) or pid <= 0:
        return None
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # Limited information is granted for all of your own processes,
        # elevated ones too: access denied means someone else's.
        return NOT_YOURS if ctypes.get_last_error() == 5 else None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            return None
        created = times[0]
        return (created.dwHighDateTime << 32) | created.dwLowDateTime
    finally:
        kernel32.CloseHandle(handle)


def pid_alive(pid: int) -> bool:
    """True if a process with this id is running.

    Not ``os.kill(pid, 0)``: on Windows signal 0 is CTRL_C_EVENT, and that call
    would interrupt the process instead of probing it.
    """
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE,
                                                ctypes.POINTER(wintypes.DWORD)]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            # Access denied still means the process exists.
            return ctypes.get_last_error() == 5
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def open_url(url: str) -> None:
    """Hand a URL to the shell (the Claude desktop app owns ``claude://``)."""
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        import subprocess

        subprocess.Popen(["open", url])
    else:
        import subprocess

        subprocess.Popen(["xdg-open", url])


def _windows_program(*parts: str) -> str:
    """A Windows program by its full path, never found by searching the
    current folder or the app's own first."""
    return os.path.join(os.environ.get("SystemRoot") or r"C:\Windows", *parts)


def edit_file(path: Path) -> None:
    """Open a text file in your own editor (What Claude Knows About You's
    Edit, #92): The Chat Place itself never writes to Claude Code's files.
    Windows tries the file type's Edit verb, then Open, then Notepad, since
    a ``.md`` file often has no program set for it. Raises OSError if none
    of them could start."""
    import subprocess

    if sys.platform == "win32":
        for verb in ("edit", "open"):
            try:
                os.startfile(str(path), verb)  # type: ignore[attr-defined]  # noqa: S606
                return
            except OSError:
                continue
        subprocess.Popen([_windows_program("System32", "notepad.exe"), str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])  # the default text editor
    else:
        subprocess.Popen(["xdg-open", str(path)])


def show_in_folder(path: Path) -> None:
    """Show a file selected in Explorer or the Finder."""
    import subprocess

    if sys.platform == "win32":
        # One command line, so the path keeps its own quotes: given as a list
        # item, Python quotes "/select,C:\a b\x.md" whole, and Explorer
        # opens Documents instead.
        subprocess.Popen(f'"{_windows_program("explorer.exe")}" /select,"{path}"')
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(Path(path).parent)])


class ClaudeLookup:
    """Where ``claude`` is, or why it can't be used: ``reason`` in a sentence
    or two, short enough to be spoken, and ``install_help`` with the
    commands, for Claude Code Sign-in's dialog."""

    def __init__(self, path: Optional[str] = None, reason: str = "",
                 install_help: str = "") -> None:
        self.path = path
        self.reason = reason
        self.install_help = install_help

    @property
    def problem(self) -> str:
        """The reason and where to go about it, for New Session, Send and
        the rest, which can't install Claude Code themselves."""
        if not self.reason:
            return ""
        return f"{self.reason} To install it, choose Claude Code Sign-in on the Help menu."


_SCRIPT_SUFFIXES = (".cmd", ".bat", ".ps1")

#: Claude Code's own install commands (https://code.claude.com/docs/en/setup),
#: shown when it can't be found and run by Claude Code Sign-in.
INSTALL_SH = "curl -fsSL https://claude.ai/install.sh | bash"
INSTALL_PS1 = "irm https://claude.ai/install.ps1 | iex"
INSTALL_CMD = ("curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd "
               "&& del install.cmd")


def claude_install_help() -> str:
    """How to install the native Claude Code, for a message box."""
    if sys.platform == "win32":
        commands = (f"In PowerShell:\n    {INSTALL_PS1}\n"
                    f"Or in Command Prompt:\n    {INSTALL_CMD}")
    else:
        commands = f"In Terminal:\n    {INSTALL_SH}"
    return (f"To install it, run its native installer. {commands}\n"
            "Then run claude once to sign in, or use Claude Code Sign-in here again.")


def _native_candidates() -> List[Path]:
    """Where the native ``claude`` is when it isn't on the PATH. An app
    started from the Finder gets only /usr/bin:/bin:/usr/sbin:/sbin, so
    on a Mac the Homebrew and npm folders are looked in by name; on Windows
    a PATH change made by an installer reaches the app only after signing
    out and in again."""
    home = Path.home()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return [home / ".local" / "bin" / "claude.exe",
                Path(local) / "Microsoft" / "WinGet" / "Links" / "claude.exe"]
    return [home / ".local" / "bin" / "claude",
            Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude"),
            home / ".npm-global" / "bin" / "claude"]


#: What an npm shim runs: ``"%dp0%\node_modules\...\claude.exe"   %*``. Only a
#: claude.exe: an old shim also names the node.exe that runs cli.js.
_SHIM_TARGET = re.compile(r'"%~?dp0%?\\((?:[^"%]*?\\)?claude\.exe)"', re.IGNORECASE)


def _native_behind_shim(script: str) -> Optional[str]:
    """The native ``claude.exe`` an npm ``claude.cmd`` starts. Newer npm
    installs of Claude Code put the same native program in node_modules, and
    started directly it takes its arguments as they are, so it is as safe as
    the native installer's."""
    try:
        text = Path(script).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _SHIM_TARGET.search(text)
    if not match:
        return None
    exe = Path(script).parent / match.group(1).replace("\\", "/")
    return str(exe) if exe.is_file() else None


def _is_node_script(path: str) -> bool:
    """An old npm install's ``claude``: a JavaScript file run by Node, which
    an app started from the Finder can't find."""
    try:
        with open(path, "rb") as f:
            first = f.read(128)
    except OSError:
        return False
    return first.startswith(b"#!") and b"node" in first.split(b"\n", 1)[0]


def find_claude(which=None, native_candidates=None) -> ClaudeLookup:
    """Find the native ``claude`` executable.

    A ``claude.cmd`` / ``.bat`` (the npm install) is never run: Windows runs
    those through cmd.exe, which re-parses the command line, so a session
    title containing ``&`` or ``"`` could run a second command. The native
    installer's ``claude.exe`` takes its arguments as they are, and so does the
    native program a newer npm install's shim starts, which is used instead.
    """
    import shutil

    which = which or shutil.which
    if native_candidates is None:
        native_candidates = _native_candidates()
    found = which("claude")
    if found and not found.lower().endswith(_SCRIPT_SUFFIXES) and not _is_node_script(found):
        return ClaudeLookup(found)
    if found and found.lower().endswith(_SCRIPT_SUFFIXES):
        native = _native_behind_shim(found)
        if native:
            return ClaudeLookup(native)
    for candidate in native_candidates:
        if Path(candidate).is_file() and not _is_node_script(str(candidate)):
            return ClaudeLookup(str(candidate))
    if found:
        return ClaudeLookup(None, (
            "The claude command on this computer is an older npm install of Claude Code, "
            "which runs as a script. The Chat Place needs the native claude program, "
            f"because a script would let a session title be read as a command. ({found})"),
            claude_install_help())
    return ClaudeLookup(None, (
        "Claude Code isn't installed, or The Chat Place can't find it. The Claude desktop "
        "app's own copy isn't on the PATH and isn't meant for other programs."),
        claude_install_help())


def claude_executable() -> Optional[str]:
    """Path to the native ``claude`` command, or None (see ``find_claude``)."""
    return find_claude().path


def run_in_terminal(argv: List[str], script_name: str = "", title: str = "",
                    env: Optional[dict] = None, clear: Iterable[str] = (),
                    clear_prefixes: Iterable[str] = ()):
    """Run a command where the user can see and answer it: a new console
    window on Windows, a Terminal window on a Mac (from a ``.command`` file
    in the app's own folder, so no permission to control Terminal is
    needed; started from the app it would have no window at all). Returns
    the Popen on Windows, to wait for; None on a Mac, where the window
    outlives ``open``. ``env`` is the Windows window's environment; Terminal
    starts the user's own shell, whose profile may set the variables
    ``env`` leaves out, so the script unsets ``clear`` and ``clear_prefixes``."""
    import shlex
    import subprocess

    if sys.platform == "win32":
        return subprocess.Popen(argv, env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
    folder = app_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / script_name
    lines = ["#!/bin/bash"]
    names = sorted(n for n in clear if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n))
    if names:
        lines.append("unset " + " ".join(names))
    patterns = "|".join(f"{p}*" for p in clear_prefixes
                        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p))
    if patterns:
        lines.append(f'for v in $(compgen -e); do case "$v" in {patterns}) unset "$v";; '
                     'esac; done')
    lines += [f"echo {shlex.quote(title)}", shlex.join(argv), "status=$?", "echo",
              'if [ "$status" -eq 0 ]; then',
              "  echo 'Finished. You can close this window and go back to The Chat Place.'",
              "else",
              '  echo "It didn\'t finish (exit code $status). You can close this window."',
              "fi"]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    script.chmod(0o700)
    subprocess.Popen(["open", "-a", "Terminal", str(script)])
    return None


def start_claude_install(env: Optional[dict] = None):
    """Run Claude Code's native installer in its own window (see
    ``run_in_terminal`` for what's returned)."""
    if sys.platform == "win32":
        powershell = _windows_program("System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        # In a scriptblock and a try, so an exit or error in the installer
        # leaves the window open to be read.
        return run_in_terminal(
            [powershell, "-NoProfile", "-Command",
             "try { & ([scriptblock]::Create((irm https://claude.ai/install.ps1))) } "
             "catch { Write-Host $_ -ForegroundColor Red } "
             "finally { Read-Host 'Finished. Press Enter to close this window' }"],
            env=env)
    return run_in_terminal(["/bin/bash", "-c", INSTALL_SH], "install-claude-code.command",
                           "Installing Claude Code with its native installer.")


CREATE_SUSPENDED = 0x00000004


class ProcessTree:
    """Lets a child process be killed together with everything it started.

    On Windows the child goes into a Job Object with KILL_ON_JOB_CLOSE, so
    terminating the job, closing it when the turn ends, or The Chat Place
    exiting ends the whole tree: claude runs tools as child processes, and
    killing only claude.exe would leave a long build or test run going. It
    also means anything Claude started and left running ends with the turn.

    The child is created suspended and only resumed once it is in the job, so
    nothing it starts can escape the job in between. If the job can't be set
    up the child is still resumed, and ``kill`` falls back to
    ``taskkill /T /F``. Elsewhere the child gets its own process group.
    """

    def __init__(self) -> None:
        self._job = None
        self._pid: Optional[int] = None

    @staticmethod
    def popen_kwargs() -> dict:
        if sys.platform == "win32":
            return {"creationflags": hidden_window_flags() | CREATE_SUSPENDED}
        return {"start_new_session": True}

    def attach(self, process) -> None:
        """Put a (suspended) child into the job, then let it run. Raises if a
        real Windows child can't be resumed, after killing it, so a turn never
        hangs on a process that was never started."""
        self._pid = getattr(process, "pid", None)
        handle = getattr(process, "_handle", None)
        if sys.platform != "win32" or not isinstance(self._pid, int) or handle is None:
            return
        try:
            self._job = _create_kill_on_close_job()
            if self._job is not None and not _assign_to_job(self._job, int(handle)):
                _close_handle(self._job)
                self._job = None
        except Exception:  # noqa: BLE001 - fall back to taskkill
            self._job = None
        if not _resume_process(int(handle)):
            try:
                process.kill()
            except OSError:
                pass
            raise OSError("Couldn't start claude (it could not be resumed).")

    def kill(self) -> None:
        if self._pid is None:
            return
        if sys.platform == "win32":
            if self._job is not None and _kernel32().TerminateJobObject(self._job, 1):
                return
            import subprocess

            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self._pid)],
                           capture_output=True, creationflags=hidden_window_flags())
            return
        import signal

        try:
            os.killpg(self._pid, signal.SIGKILL)
        except OSError:
            pass

    def close(self) -> None:
        """Close the job. KILL_ON_JOB_CLOSE ends anything still in it."""
        if self._job is not None:
            _close_handle(self._job)
            self._job = None


_K32 = None


def _kernel32():
    """kernel32 with argument and result types declared, so 64-bit handles
    are passed whole instead of being truncated to C ints."""
    global _K32
    if _K32 is not None:
        return _K32
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                          wintypes.LPVOID, wintypes.DWORD]
    k.SetInformationJobObject.restype = wintypes.BOOL
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.AssignProcessToJobObject.restype = wintypes.BOOL
    k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.TerminateJobObject.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    _K32 = k
    return k


def _resume_process(handle: int) -> bool:
    """Resume a process created with CREATE_SUSPENDED (its only thread)."""
    import ctypes
    from ctypes import wintypes

    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtResumeProcess.restype = ctypes.c_long
    return ntdll.NtResumeProcess(handle) == 0


def _create_kill_on_close_job():
    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k = _kernel32()
    job = k.CreateJobObjectW(None, None)
    if not job:
        return None
    info = EXTENDED()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not k.SetInformationJobObject(job, 9,  # JobObjectExtendedLimitInformation
                                     ctypes.byref(info), ctypes.sizeof(info)):
        _close_handle(job)
        return None
    return job


def _assign_to_job(job, process_handle: int) -> bool:
    return bool(_kernel32().AssignProcessToJobObject(job, process_handle))


def _close_handle(handle) -> None:
    _kernel32().CloseHandle(handle)


def bring_window_forward(title_matches) -> bool:
    """Bring the first top-level window whose title satisfies ``title_matches``
    to the front. Windows only; returns False elsewhere or if none matched."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if title_matches(buffer.value):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    if not found:
        return False
    hwnd = found[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    return bool(user32.SetForegroundWindow(hwnd))


def bring_last_popup_forward(hwnd: int) -> bool:
    """Bring forward ``hwnd``'s open dialog: the frontmost visible, enabled
    window it owns, directly or through another dialog, so the innermost of
    nested dialogs, native message and file dialogs included (#103). For a
    main window that was activated while disabled behind a dialog. Windows
    only; False elsewhere, or if there is none.

    Not GetLastActivePopup: activating the main window makes it its own last
    active popup, so that answered with the main window (seen in the VM)."""
    if sys.platform != "win32" or not hwnd:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
    gw_owner = 4
    found = []

    def owned_by_main(window) -> bool:
        for _ in range(8):  # a dialog over a dialog over the main window
            window = user32.GetWindow(window, gw_owner)
            if not window:
                return False
            if window == hwnd:
                return True
        return False

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(window, _lparam):
        # EnumWindows goes front to back, so the first match is the front one.
        if (window != hwnd and user32.IsWindowVisible(window)
                and user32.IsWindowEnabled(window) and owned_by_main(window)):
            found.append(window)
            return False
        return True

    user32.EnumWindows(callback, 0)
    return bool(found) and bool(user32.SetForegroundWindow(found[0]))


def hidden_window_flags() -> int:
    """creationflags that keep a console window from flashing up on Windows."""
    if sys.platform == "win32":
        import subprocess

        return subprocess.CREATE_NO_WINDOW
    return 0
