"""Saved prompts (#131): the store, without wx."""
import json

import pytest

from thechatplace import platform_paths
from thechatplace.prompts import MAX_NAME, PromptStore, suggested_name


def test_missing_file_is_an_empty_library(tmp_path):
    store = PromptStore(tmp_path / "prompts.json")
    assert store.all() == [] and store.load_error == ""
    assert not (tmp_path / "prompts.json").exists()  # nothing written by reading


def test_default_path_is_in_the_apps_own_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_paths, "app_data_dir", lambda: tmp_path / "appdata")
    store = PromptStore()
    store.add("Hi", "Hello")
    assert store.path == tmp_path / "appdata" / "prompts.json" and store.path.is_file()


def test_round_trip_keeps_order_text_and_line_breaks(tmp_path):
    path = tmp_path / "prompts.json"
    store = PromptStore(path)
    store.add("Review", "Review this change.\n\nBe thorough — check tests.")
    store.add("  Two   words ", "  Second\n")
    again = PromptStore(path)
    assert again.names() == ["Review", "Two words"]
    assert again.get(0).text == "Review this change.\n\nBe thorough — check tests."
    assert again.get(1).text == "Second"
    assert "—" in path.read_text(encoding="utf-8")  # kept readable, not \u escapes


def test_names_must_be_unique_ignoring_case_and_not_empty(tmp_path):
    store = PromptStore(tmp_path / "prompts.json")
    store.add("Review", "a")
    with pytest.raises(ValueError, match="already a prompt called Review"):
        store.add("review", "b")
    with pytest.raises(ValueError, match="needs a name"):
        store.add("   ", "b")
    with pytest.raises(ValueError, match="needs some text"):
        store.add("Other", " \n ")
    assert store.names() == ["Review"]
    # Renaming a prompt to its own name in another case is fine.
    store.update(0, "REVIEW", "a2")
    assert store.all()[0].name == "REVIEW" and store.get(0).text == "a2"
    assert len(store.get(store.add("x" * 200, "long")).name) == MAX_NAME


def test_delete_and_move(tmp_path):
    store = PromptStore(tmp_path / "prompts.json")
    for name in ("A", "B", "C"):
        store.add(name, name.lower())
    assert store.move(0, -1) == 0  # already first: nothing changes
    assert store.move(0, 1) == 1 and store.names() == ["B", "A", "C"]
    assert store.move(2, 1) == 2
    assert store.delete(1).name == "A"
    assert PromptStore(store.path).names() == ["B", "C"]
    with pytest.raises(ValueError):
        store.delete(5)


@pytest.mark.parametrize("content", ["{not json", json.dumps(["a list"]),
                                     json.dumps({"prompts": "nope"})])
def test_damaged_file_is_kept_aside_never_thrown_away(tmp_path, content):
    path = tmp_path / "prompts.json"
    path.write_text(content, encoding="utf-8")
    store = PromptStore(path)
    assert store.all() == []
    backups = list(tmp_path.glob("prompts.json.bad-*"))
    assert len(backups) == 1 and backups[0] == store.backup_path
    assert backups[0].read_text(encoding="utf-8") == content
    assert str(path) in store.load_error and backups[0].name in store.load_error
    store.add("New", "text")  # a fresh library, with the old file still beside it
    assert PromptStore(path).names() == ["New"]
    assert backups[0].read_text(encoding="utf-8") == content


def test_damaged_file_that_cannot_be_moved_is_never_saved_over(tmp_path, monkeypatch):
    path = tmp_path / "prompts.json"
    path.write_text("{not json", encoding="utf-8")
    from thechatplace import prompts

    def refuse(src, dst):
        raise OSError("in use")
    monkeypatch.setattr(prompts.os, "replace", refuse)
    store = PromptStore(path)
    assert "couldn't be moved aside" in store.load_error
    with pytest.raises(OSError):
        store.add("New", "text")
    assert store.all() == [] and path.read_text(encoding="utf-8") == "{not json"


def test_unreadable_file_is_left_alone(tmp_path, monkeypatch):
    path = tmp_path / "prompts.json"
    path.write_text(json.dumps({"prompts": [{"name": "A", "text": "a"}]}), encoding="utf-8")
    from pathlib import Path

    def locked(self, *a, **k):
        raise PermissionError("locked")
    monkeypatch.setattr(Path, "read_text", locked)
    store = PromptStore(path)
    monkeypatch.undo()
    assert "Couldn't read your saved prompts" in store.load_error
    with pytest.raises(OSError):
        store.add("B", "b")
    assert PromptStore(path).names() == ["A"]


def test_bad_entries_are_skipped_and_good_ones_kept(tmp_path):
    path = tmp_path / "prompts.json"
    path.write_text(json.dumps({"version": 1, "prompts": [
        {"name": "Good", "text": "fine"}, "junk", {"name": "", "text": "x"},
        {"name": "No text"}, {"name": "good", "text": "duplicate"},
        {"name": "Number", "text": 5}]}), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    store = PromptStore(path)
    assert store.names() == ["Good"]
    # Not dropped silently: said, and the file as it was is copied aside.
    assert "5 entries" in store.load_error and store.backup_path.name in store.load_error
    assert store.backup_path.read_text(encoding="utf-8") == before
    assert path.read_text(encoding="utf-8") == before


def test_a_file_saved_with_a_byte_order_mark_is_read(tmp_path):
    path = tmp_path / "prompts.json"
    path.write_text(json.dumps({"prompts": [{"name": "A", "text": "a"}]}), encoding="utf-8-sig")
    store = PromptStore(path)
    assert store.names() == ["A"] and store.load_error == ""


def test_a_failed_save_leaves_the_library_as_it_was(tmp_path, monkeypatch):
    store = PromptStore(tmp_path / "prompts.json")
    store.add("A", "a")

    def fail():
        raise OSError("disk full")
    monkeypatch.setattr(store, "save", fail)
    with pytest.raises(OSError):
        store.add("B", "b")
    with pytest.raises(OSError):
        store.delete(0)
    assert store.names() == ["A"]


def test_suggested_and_unique_names(tmp_path):
    assert suggested_name("Please review\nthe   tests and fix what fails today") == \
        "Please review the tests and fix"
    assert suggested_name("x" * 100) == "x" * 40
    assert suggested_name("averyveryverylongfirstwordthatgoesonandon and more") == \
        "averyveryverylongfirstwordthatgoesonando"
    store = PromptStore(tmp_path / "prompts.json")
    assert store.unique_name("Review") == "Review"
    store.add("Review", "a")
    assert store.unique_name("review") == "review (2)"
    store.add("Review (2)", "b")
    assert store.unique_name("Review") == "Review (3)"
    assert len(store.unique_name("y" * MAX_NAME)) <= MAX_NAME
    assert store.unique_name("   ") == "Prompt"
