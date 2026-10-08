"""Write the keyboard shortcuts and the user guide into docs/, from what the app
itself shows on F1 (``thechatplace/ui_text.py``) and on Help, User Guide
(``thechatplace/assets/user-guide.md``), so they never disagree:

    python tools/make_docs.py

docs/keyboard-shortcuts.html  a page to read, or to open and copy into an email
docs/keyboard-shortcuts.md    the same as Markdown tables, for GitHub
docs/keyboard-shortcuts.txt   plain text
docs/user-guide.html          the user guide as a page, made like the app's (#102)
docs/user-guide.md            the same Markdown, for GitHub

The guide is edited in thechatplace/assets/user-guide.md, never in docs/.
tests/test_docs.py fails if these are out of date.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from thechatplace.platform_paths import user_guide_path  # noqa: E402
from thechatplace.rendering import html_page, message_page  # noqa: E402
from thechatplace.ui_text import LAYOUT, SHORTCUTS, shortcuts_html, shortcuts_text  # noqa: E402

DOCS = ROOT / "docs"
TITLE = "The Chat Place keyboard shortcuts"
GUIDE_TITLE = "The Chat Place User Guide"


def _markdown() -> str:
    lines = [f"# {TITLE}", "", LAYOUT, ""]
    for group, items in SHORTCUTS:
        lines += [f"## {group}", "", "| Keys | What it does |", "| --- | --- |"]
        for key, action in items:
            lines.append(f"| {key.replace('|', '&#124;')} | {action.replace('|', '&#124;')} |")
        lines.append("")
    return "\n".join(lines)


def documents() -> Dict[str, str]:
    """Each file's name and what it should hold."""
    guide = user_guide_path().read_text(encoding="utf-8")
    return {
        "keyboard-shortcuts.html": html_page(TITLE, shortcuts_html()) + "\n",
        "keyboard-shortcuts.md": _markdown(),
        "keyboard-shortcuts.txt": f"{TITLE}\n\n{shortcuts_text()}\n",
        "user-guide.html": message_page(GUIDE_TITLE, guide) + "\n",
        "user-guide.md": guide,
    }


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    for name, text in documents().items():
        (DOCS / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote docs/{name}")


if __name__ == "__main__":
    main()
