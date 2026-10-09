"""Where a new session works (#154): the folders sessions have used, a
GitHub repository (cloned under the GitHub folder when it isn't there yet),
and a new git worktree on a branch of its own.

Plain data and subprocess calls, no wx, so it can be tested on its own.
Every ``git`` and ``gh`` call is an argument list with no shell, and names
that reach one (a repository, a branch) are checked first.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from . import platform_paths

#: How many recent folders New Session offers.
RECENT_LIMIT = 20
#: How many of your repositories From GitHub lists.
REPO_LIMIT = 300

#: GitHub's own rule for owner and repository names, near enough: letters,
#: digits, "-", "_" and "."; never starting with "-" (it would read as an
#: option) or being "." or "..".
_PART = r"[A-Za-z0-9_.][A-Za-z0-9_.-]{0,99}"
_REPO = re.compile(rf"^({_PART})/({_PART})$")
_REPO_URL = re.compile(
    rf"^(?:https?://(?:www\.)?github\.com/|git@github\.com:)({_PART})/({_PART}?)(?:\.git)?/?$",
    re.IGNORECASE)


class ToolError(Exception):
    """A git or gh step that failed, with a message to show as it is."""


# -- recent folders -----------------------------------------------------------------------

def repo_of_worktree(folder: str) -> str:
    """The repository a ``<repo>/.claude/worktrees/<name>`` folder belongs
    to, or the folder itself if it isn't one of those."""
    match = re.search(r"[\\/]\.claude[\\/]worktrees[\\/][^\\/]+[\\/]?$", folder)
    return folder[:match.start()] if match and match.start() > 0 else folder


def recent_folders(sessions: Iterable, limit: int = RECENT_LIMIT,
                   exists: Callable[[str], bool] = os.path.isdir) -> List[str]:
    """The folders ``sessions`` (SessionInfo) have worked in, most recently
    used first, each once. A worktree counts as its repository, a Cowork
    session (whose folder is its own "outputs" folder) not at all, and a
    folder that no longer exists is left out."""
    ordered = sorted((s for s in sessions if not getattr(s, "cowork", False) and s.cwd),
                     key=lambda s: s.last_activity_ms or 0, reverse=True)
    seen = set()
    folders = []
    for info in ordered:
        folder = repo_of_worktree(info.cwd.rstrip("\\/") or info.cwd)
        key = os.path.normcase(os.path.normpath(folder))
        if key in seen:
            continue
        seen.add(key)
        if exists(folder):
            folders.append(folder)
            if len(folders) >= limit:
                break
    return folders


# -- running git and gh -------------------------------------------------------------------

def _environment() -> dict:
    """Never stop to ask for a password or a passphrase: there is no
    terminal to answer it in, and the call would hang."""
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_ASKPASS="",
               SSH_ASKPASS="", GCM_INTERACTIVE="never", GH_NO_UPDATE_NOTIFIER="1")
    return env


def _run(argv: List[str], cwd: Optional[str] = None, timeout: float = 30) -> str:
    """stdout, or ToolError with what the program said."""
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout,
                              stdin=subprocess.DEVNULL, env=_environment(),
                              creationflags=platform_paths.hidden_window_flags())
    except subprocess.TimeoutExpired:
        raise ToolError(f"{Path(argv[0]).stem} took too long to answer.") from None
    except OSError as exc:
        raise ToolError(f"Couldn't run {Path(argv[0]).stem}: {exc}") from None
    if done.returncode != 0:
        said = " ".join((done.stderr or done.stdout or "").split())
        raise ToolError(said or f"{Path(argv[0]).stem} failed (exit {done.returncode}).")
    return done.stdout


def find_git() -> Optional[str]:
    return platform_paths.find_tool("git")


def find_gh() -> Optional[str]:
    return platform_paths.find_tool("gh")


def _gh(gh: str) -> List[str]:
    """How ``gh`` is started (the tests start a fake one through Python)."""
    return [gh]


GH_MISSING = ("The GitHub CLI (gh) isn't installed, or The Chat Place can't find it. Install it "
              "from https://cli.github.com, run gh auth login once, then try again. You can "
              "still type a folder or use Browse.")


# -- GitHub repositories ------------------------------------------------------------------

@dataclass
class GitHubRepo:
    name: str               # owner/name
    description: str = ""
    private: bool = False

    @property
    def short_name(self) -> str:
        return self.name.split("/", 1)[1]

    def row(self) -> str:
        text = f"{self.name}{', private' if self.private else ''}"
        description = " ".join(self.description.split())
        if len(description) > 160:
            description = description[:159] + "…"
        return f"{text}: {description}" if description else text


def parse_repo(text: str) -> Optional[str]:
    """``owner/name`` from what was typed (``owner/name`` or a GitHub
    address), or None if it isn't one."""
    text = (text or "").strip()
    for pattern in (_REPO, _REPO_URL):
        match = pattern.match(text)
        if match:
            owner, name = match.group(1), match.group(2)
            if name.lower().endswith(".git"):
                name = name[:-4]
            if owner in (".", "..") or name in (".", "..", ""):
                return None
            return f"{owner}/{name}"
    return None


def list_github_repos(gh: str, limit: int = REPO_LIMIT) -> List[GitHubRepo]:
    """Your repositories, as ``gh repo list`` gives them (most recently
    pushed first). Uses gh's own sign-in; ToolError if it can't."""
    out = _run([*_gh(gh), "repo", "list", "--limit", str(limit),
                "--json", "nameWithOwner,description,isPrivate"], timeout=60)
    try:
        items = json.loads(out or "[]")
    except ValueError:
        raise ToolError("gh gave an answer The Chat Place couldn't read.") from None
    repos = []
    for item in items if isinstance(items, list) else []:
        name = parse_repo(str(item.get("nameWithOwner") or "")) if isinstance(item, dict) else None
        if name:
            repos.append(GitHubRepo(name, str(item.get("description") or ""),
                                    bool(item.get("isPrivate"))))
    return repos


def clone_target(root: Path, repo: str) -> Path:
    """Where ``repo`` is cloned: its own name under the GitHub folder."""
    return Path(root) / repo.split("/", 1)[1]


_REMOTE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", re.IGNORECASE)


def is_clone_of(git: str, folder: Path, repo: str) -> bool:
    """Whether ``folder`` is a clone of ``repo``: a repository of its own
    (not a folder inside some other one) whose origin is ``repo``."""
    try:
        top = _run([git, "-C", str(folder), "rev-parse", "--show-toplevel"], timeout=10).strip()
        if not top or os.path.normcase(os.path.realpath(top)) != \
                os.path.normcase(os.path.realpath(folder)):
            return False
        url = _run([git, "-C", str(folder), "remote", "get-url", "origin"], timeout=10).strip()
    except ToolError:
        return False
    match = _REMOTE.search(url)
    return bool(match) and f"{match.group(1)}/{match.group(2)}".lower() == repo.lower()


class Clone:
    """``gh repo clone`` running in the background, which can be cancelled.

    ``done(folder, error)`` is called on the clone's own thread, once: the
    folder and "" when it worked, or None and why not. A cancelled clone
    removes the folder it had started, which it made itself.
    """

    def __init__(self, gh: str, repo: str, target: Path,
                 done: Callable[[Optional[Path], str], None]) -> None:
        self.repo, self.target = repo, Path(target)
        self._done = done
        self._cancelled = threading.Event()
        self._process: Optional[subprocess.Popen] = None
        self._argv = [*_gh(gh), "repo", "clone", repo, str(self.target)]
        self._thread = threading.Thread(target=self._run, name="clone", daemon=True)

    def start(self) -> "Clone":
        self._thread.start()
        return self

    def cancel(self) -> None:
        self._cancelled.set()
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass

    def wait(self, timeout: Optional[float] = None) -> None:
        self._thread.join(timeout)

    def _run(self) -> None:
        if self.target.exists():
            # Checked by the caller too; never clone into something that's there.
            self._done(None, f"{self.target} already exists.")
            return
        try:
            self._process = subprocess.Popen(
                self._argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                env=_environment(), creationflags=platform_paths.hidden_window_flags())
            if self._cancelled.is_set():
                self._process.kill()
            _out, err = self._process.communicate(timeout=60 * 60)
        except (OSError, subprocess.SubprocessError) as exc:
            self._finish(None, f"Couldn't clone {self.repo}: {exc}")
            return
        if self._cancelled.is_set():
            self._finish(None, "")
        elif self._process.returncode != 0:
            said = " ".join((err or "").split())
            self._finish(None, f"Couldn't clone {self.repo}. {said}".strip())
        else:
            self._done(self.target, "")

    def _finish(self, folder, error: str) -> None:
        if self.target.is_dir():
            import shutil
            shutil.rmtree(self.target, ignore_errors=True)
        self._done(folder, error)


# -- branches and worktrees ---------------------------------------------------------------

@dataclass
class RepoInfo:
    top: str                 # the repository's own folder
    branch: str              # checked out now ("" when detached)
    branches: List[str]      # local branches


def repo_info(git: str, folder: str) -> Optional[RepoInfo]:
    """The git repository ``folder`` is in, or None if it isn't in one."""
    if not folder or not os.path.isdir(folder):
        return None
    try:
        top = _run([git, "-C", folder, "rev-parse", "--show-toplevel"], timeout=10).strip()
        branch = _run([git, "-C", folder, "branch", "--show-current"], timeout=10).strip()
        listed = _run([git, "-C", folder, "for-each-ref", "--format=%(refname:short)",
                       "refs/heads/"], timeout=10)
    except ToolError:
        return None
    if not top:
        return None
    branches = [line.strip() for line in listed.splitlines() if line.strip()]
    if branch in branches:  # the current one first
        branches.remove(branch)
        branches.insert(0, branch)
    return RepoInfo(str(Path(top)), branch, branches)


def check_branch_name(git: str, name: str) -> str:
    """``name`` if git accepts it as a branch name, else ToolError. Names
    that git would read as an option or as ``@{-1}`` shorthand are refused
    before git sees them."""
    name = (name or "").strip()
    if not name:
        raise ToolError("Type a branch name, or choose one.")
    if name.startswith(("-", "@")) or "@{" in name or any(c.isspace() for c in name):
        raise ToolError(f"{name} can't be a branch name.")
    try:
        _run([git, "check-ref-format", "--branch", name], timeout=10)
    except ToolError:
        raise ToolError(f"{name} can't be a branch name.") from None
    return name


def worktree_folder(top: str, branch: str) -> Path:
    """``<repo>/.claude/worktrees/<branch>``, where Claude Code and the
    desktop app put theirs; "/" in a branch name becomes "-", and a number
    is added if the folder is taken."""
    base = Path(top) / ".claude" / "worktrees"
    name = re.sub(r"[^A-Za-z0-9._-]", "-", branch).strip(".-") or "worktree"
    folder, number = base / name, 2
    while folder.exists():
        folder, number = base / f"{name}-{number}", number + 1
    return folder


def add_worktree(git: str, top: str, branch: str, branches: Iterable[str]) -> Path:
    """Make a worktree for ``branch`` and return its folder: an existing
    branch is checked out there, a new one is made from what the repository
    has checked out now. ToolError with git's words if it can't (the branch
    is already checked out somewhere else, say)."""
    branch = check_branch_name(git, branch)
    folder = worktree_folder(top, branch)
    if branch in set(branches):
        argv = [git, "-C", top, "worktree", "add", "--", str(folder), branch]
    else:
        argv = [git, "-C", top, "worktree", "add", "-b", branch, "--", str(folder)]
    _run(argv, timeout=300)
    return folder
