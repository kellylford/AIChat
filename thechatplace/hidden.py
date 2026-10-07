"""Sessions you've hidden from the list (File, Hide Session): The Chat Place's
own and the desktop app's alike. Nothing about the session itself changes;
the list just leaves it out, except in View, Show Sessions, Hidden, where
File, Bring Back Session shows it again. Kept in ``hidden.json``.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Set

from . import platform_paths


class HiddenStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else platform_paths.app_data_dir() / "hidden.json"
        self._keys: Set[str] = set()
        self.load_error = ""
        self.load()

    def load(self) -> None:
        self._keys = set()
        self.load_error = ""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            self.load_error = f"Couldn't read your hidden sessions ({self.path}): {exc}"
            return
        keys = raw.get("hidden") if isinstance(raw, dict) else None
        if not isinstance(keys, list):
            self.load_error = (f"Your hidden sessions file ({self.path}) isn't in the "
                               "expected format, so The Chat Place won't change it.")
            return
        self._keys = {k for k in keys if isinstance(k, str) and k}

    def keys(self) -> List[str]:
        return sorted(self._keys)

    def __contains__(self, key: str) -> bool:
        return key in self._keys

    def hide(self, key: str) -> None:
        self._change(self._keys | {key})

    def show(self, key: str) -> None:
        self._change(self._keys - {key})

    def rename_key(self, old: str, new: str) -> None:
        if old in self._keys:
            self._change((self._keys - {old}) | {new})

    def _change(self, keys: Set[str]) -> None:
        """Save, then keep: a change that can't be saved isn't made."""
        if self.load_error:
            raise OSError(f"Not saving over the unreadable {self.path}.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="hidden-", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "hidden": sorted(keys)}, handle, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self._keys = set(keys)
