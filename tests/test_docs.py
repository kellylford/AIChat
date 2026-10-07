"""docs/ keeps up with the app's own keyboard shortcuts list."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _make_docs():
    spec = importlib.util.spec_from_file_location("make_docs", ROOT / "tools" / "make_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_shortcut_documents_match_the_app():
    for name, text in _make_docs().documents().items():
        path = ROOT / "docs" / name
        assert path.is_file(), f"run python tools/make_docs.py (docs/{name} is missing)"
        assert path.read_text(encoding="utf-8") == text, \
            f"run python tools/make_docs.py (docs/{name} is out of date)"
