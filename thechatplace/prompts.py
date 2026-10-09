"""Saved prompts (#131): a library of messages you send often.

Each prompt is a name (one line, shown in the list) and its text (any
length, line breaks kept). Kept in ``%APPDATA%\\TheChatPlace\\prompts.json``
(on a Mac, ``~/Library/Application Support/TheChatPlace``) and written as the
groups are: to a temporary file that then replaces the real one, so a crash
mid-write never leaves half a file. Nothing of Claude's is read or written:
Claude Code's own history (``~/.claude/history.jsonl``) is left alone.

A missing file is an empty library. A damaged one is never silently thrown
away, as with the session list (``own_store``): one that isn't JSON, or isn't
in the expected shape, is moved aside to ``prompts.json.bad-<when>`` and the
library starts empty; one that can't be read just now (locked by a sync tool,
say) may be fine, so nothing is saved over it this run. Either way
``load_error`` says what happened.
"""
from __future__ import annotations

import dataclasses
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from . import platform_paths

#: Longest prompt name kept; longer ones are cut.
MAX_NAME = 80
#: Words of a message used for a prompt's suggested name.
NAME_WORDS = 6
#: Longest suggested name, before it's made unique.
SUGGESTED_NAME = 40


@dataclasses.dataclass(frozen=True)
class Prompt:
    name: str
    text: str


def clean_name(name: str) -> str:
    """A prompt name on one line, without extra spaces, at most MAX_NAME."""
    return " ".join((name or "").split())[:MAX_NAME].strip()


def clean_text(text: str) -> str:
    """The text as it will be sent: blank lines and spaces at either end
    go (as Send drops them), line breaks within it stay."""
    return (text or "").strip()


def suggested_name(text: str) -> str:
    """A name for a prompt made from a message: its first few words, on
    one line, short enough to read in a list."""
    words = clean_name(text).split()[:NAME_WORDS]
    name = ""
    for word in words:
        longer = f"{name} {word}".strip()
        if len(longer) > SUGGESTED_NAME:
            break
        name = longer
    # One very long first word: cut it rather than have no name at all.
    return name or clean_name(text)[:SUGGESTED_NAME].strip()


class PromptStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else platform_paths.app_data_dir() / "prompts.json"
        self._prompts: List[Prompt] = []
        #: Why the file couldn't be read, or "" when it could (or wasn't there).
        self.load_error = ""
        #: Where a damaged file was moved, when one was.
        self.backup_path: Optional[Path] = None
        self._save_blocked = False
        self.load()

    # -- persistence ----------------------------------------------------------

    def load(self) -> None:
        self._prompts = []
        self.load_error = ""
        self._save_blocked = False
        try:
            # utf-8-sig: the one store meant to be readable, so it may be
            # saved by hand from an editor that adds a byte-order mark.
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return
        except OSError as exc:
            self.load_error = (f"Couldn't read your saved prompts ({self.path}): {exc}. "
                               "Changes to them won't be saved until The Chat Place is "
                               "restarted and can read the file.")
            self._save_blocked = True
            return
        except ValueError as exc:
            self._set_aside(f"isn't valid JSON ({exc})")
            return
        items = raw.get("prompts") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            self._set_aside("isn't in the expected format")
            return
        seen = set()
        skipped = 0
        for item in items:
            name = clean_name(str(item.get("name") or "")) if isinstance(item, dict) else ""
            text = item.get("text") if isinstance(item, dict) else None
            if (not name or not isinstance(text, str) or not clean_text(text)
                    or name.casefold() in seen):
                skipped += 1
                continue
            seen.add(name.casefold())
            self._prompts.append(Prompt(name, clean_text(text)))
        if skipped:
            self._copy_aside(skipped)

    def _backup_path(self) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.name}.bad-{stamp}")
        n = 2
        while backup.exists():  # two damaged files in one second
            backup = self.path.with_name(f"{self.path.name}.bad-{stamp}-{n}")
            n += 1
        return backup

    def _copy_aside(self, skipped: int) -> None:
        """Some entries couldn't be used (no name, no text, a name twice):
        the rest are kept, but the next save would write the file without
        them, so a copy of it as it was goes beside it first."""
        backup = self._backup_path()
        entries = f"{skipped} entr{'y' if skipped == 1 else 'ies'}"
        try:
            shutil.copy2(self.path, backup)
        except OSError as exc:
            self.load_error = (f"{entries.capitalize()} in your saved prompts ({self.path}) "
                               f"couldn't be used, and a copy of the file couldn't be made "
                               f"({exc}). Changes to your prompts won't be saved until it "
                               "is fixed or removed.")
            self._save_blocked = True
            return
        self.backup_path = backup
        self.load_error = (f"{entries.capitalize()} in your saved prompts ({self.path}) "
                           "couldn't be used (a prompt needs a name and some text, and a "
                           f"name only once), so they're left out. A copy of the file as it "
                           f"was is in {backup.name} in the same folder.")

    def _set_aside(self, why: str) -> None:
        """Move a damaged file out of the way, so no save can write over
        whatever is in it, and say where it went."""
        backup = self._backup_path()
        try:
            os.replace(self.path, backup)
        except OSError as exc:
            self.load_error = (f"Your saved prompts ({self.path}) {why}, and the file "
                               f"couldn't be moved aside ({exc}). Changes to your prompts "
                               "won't be saved until it is fixed or removed.")
            self._save_blocked = True
            return
        self.backup_path = backup
        self.load_error = (f"Your saved prompts ({self.path}) {why}. The file was moved to "
                           f"{backup.name} in the same folder, and your prompts start empty.")

    def save(self) -> None:
        if self._save_blocked:
            raise OSError(f"Not saving over the unreadable {self.path}.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "prompts": [{"name": p.name, "text": p.text}
                                              for p in self._prompts]}
        fd, tmp = tempfile.mkstemp(prefix="prompts-", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- reading --------------------------------------------------------------

    def all(self) -> List[Prompt]:
        return list(self._prompts)

    def names(self) -> List[str]:
        return [p.name for p in self._prompts]

    def __len__(self) -> int:
        return len(self._prompts)

    def get(self, index: int) -> Prompt:
        return self._prompts[index]

    def find(self, name: str) -> Optional[int]:
        """The index of the prompt with this name, ignoring case, or None."""
        wanted = clean_name(name).casefold()
        return next((i for i, p in enumerate(self._prompts) if p.name.casefold() == wanted),
                    None)

    def unique_name(self, name: str) -> str:
        """``name``, or ``name (2)``, ``name (3)``…, whichever isn't taken."""
        name = clean_name(name) or "Prompt"
        if self.find(name) is None:
            return name
        n = 2
        while True:
            suffix = f" ({n})"
            candidate = name[:MAX_NAME - len(suffix)].rstrip() + suffix
            if self.find(candidate) is None:
                return candidate
            n += 1

    # -- changes (each saves; a change that can't be saved is undone) ----------

    def _commit(self, prompts: List[Prompt]) -> None:
        before = self._prompts
        self._prompts = prompts
        try:
            self.save()
        except Exception:
            self._prompts = before
            raise

    def _checked(self, name: str, text: str, ignore: Optional[int] = None) -> Prompt:
        name, text = clean_name(name), clean_text(text)
        if not name:
            raise ValueError("A prompt needs a name.")
        if not text:
            raise ValueError("A prompt needs some text.")
        clash = self.find(name)
        if clash is not None and clash != ignore:
            raise ValueError(f"There's already a prompt called {self._prompts[clash].name}.")
        return Prompt(name, text)

    def add(self, name: str, text: str) -> int:
        """Add a prompt at the end; returns its index."""
        prompt = self._checked(name, text)
        self._commit(self._prompts + [prompt])
        return len(self._prompts) - 1

    def update(self, index: int, name: str, text: str) -> int:
        """Change a prompt's name and text, in the same place."""
        if not 0 <= index < len(self._prompts):
            raise ValueError("That prompt is no longer there.")
        prompt = self._checked(name, text, ignore=index)
        prompts = list(self._prompts)
        prompts[index] = prompt
        self._commit(prompts)
        return index

    def delete(self, index: int) -> Prompt:
        if not 0 <= index < len(self._prompts):
            raise ValueError("That prompt is no longer there.")
        prompts = list(self._prompts)
        gone = prompts.pop(index)
        self._commit(prompts)
        return gone

    def move(self, index: int, step: int) -> int:
        """Move a prompt up (step -1) or down (+1); returns where it is now,
        the same index when it's already at that end."""
        if not 0 <= index < len(self._prompts):
            raise ValueError("That prompt is no longer there.")
        target = index + step
        if not 0 <= target < len(self._prompts):
            return index
        prompts = list(self._prompts)
        prompts[index], prompts[target] = prompts[target], prompts[index]
        self._commit(prompts)
        return target
