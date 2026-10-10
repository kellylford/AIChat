"""Comparing a probe run with the baseline (#155), on made-up pictures."""
import json
import sys
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import ui_compare  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = wx.App(False)
    yield instance


def _control(cls, label, rect, **extra):
    return {"class": cls, "name": cls.lower(), "label": label, "rect": rect,
            "best": rect[2:], "depth": 0, "enabled": True, "problems": [], **extra}


def _picture(path, box=None, colour=(0, 0, 0)):
    image = wx.Image(80, 60)
    image.SetRGB(wx.Rect(0, 0, 80, 60), 255, 255, 255)
    if box:
        image.SetRGB(wx.Rect(*box), *colour)
    image.SaveFile(str(path), wx.BITMAP_TYPE_PNG)


def _surface(folder, stem, controls, box=None, colour=(0, 0, 0), title="Settings"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stem}.json").write_text(json.dumps(
        {"title": title, "size": [80, 60], "controls": controls}), encoding="utf-8")
    _picture(folder / f"{stem}.png", box, colour)


def test_layout_changes_are_said_in_words():
    old = {"title": "Settings", "controls": [_control("Button", "OK", [10, 10, 80, 24]),
                                             _control("Button", "Cancel", [100, 10, 80, 24])]}
    new = {"title": "Settings", "controls": [
        _control("Button", "OK", [10, 40, 80, 24]),
        _control("Button", "Apply", [100, 10, 80, 24]),
        _control("StaticText", "Voice", [10, 70, 30, 20],
                 problems=["text cut off: smaller than its best size"])]}
    changes = ui_compare.layout_changes(old, new)
    assert "Button 'Cancel' is gone" in changes
    assert "Button 'Apply' is new" in changes
    assert "Button 'OK' moved from (10, 10) to (10, 40)" in changes
    assert not any("StaticText" in c and "now" in c for c in changes)  # it's new, said above


def test_a_pixel_or_two_of_movement_is_not_a_change():
    old = {"controls": [_control("Button", "OK", [10, 10, 80, 24])]}
    new = {"controls": [_control("Button", "OK", [11, 12, 81, 24])]}
    assert ui_compare.layout_changes(old, new) == []


def test_a_new_problem_on_a_control_is_reported():
    old = {"controls": [_control("Button", "OK", [10, 10, 80, 24])]}
    new = {"controls": [_control("Button", "OK", [10, 10, 80, 24],
                                 problems=["text cut off: smaller than its best size"])]}
    assert ui_compare.layout_changes(old, new) == [
        "Button 'OK': now text cut off: smaller than its best size"]


def test_same_pictures_and_layout_are_unchanged(app, tmp_path):
    controls = [_control("Button", "OK", [10, 10, 40, 20])]
    _surface(tmp_path / "base", "settings-light-100", controls, box=(5, 5, 10, 10))
    _surface(tmp_path / "run", "settings-light-100", controls, box=(5, 5, 10, 10))
    result = ui_compare.compare(tmp_path / "run", tmp_path / "base")
    assert result == {"new": [], "missing": [], "unchanged": ["settings-light-100"],
                      "changed": {}}


def test_a_colour_change_the_layout_cant_see_is_caught(app, tmp_path):
    controls = [_control("Button", "OK", [10, 10, 40, 20])]
    _surface(tmp_path / "base", "settings-dark-100", controls, box=(10, 10, 40, 30))
    _surface(tmp_path / "run", "settings-dark-100", controls, box=(10, 10, 40, 30),
             colour=(255, 0, 255))
    result = ui_compare.compare(tmp_path / "run", tmp_path / "base")
    assert list(result["changed"]) == ["settings-dark-100"]
    assert result["changed"]["settings-dark-100"] == ["25.0% of the picture's pixels changed"]
    assert (tmp_path / "run" / "diff" / "settings-dark-100.png").exists()


def test_slight_anti_aliasing_differences_are_ignored(app, tmp_path):
    controls = []
    _surface(tmp_path / "base", "usage-light-100", controls, box=(0, 0, 40, 30),
             colour=(100, 100, 100))
    _surface(tmp_path / "run", "usage-light-100", controls, box=(0, 0, 40, 30),
             colour=(110, 108, 104))
    assert ui_compare.compare(tmp_path / "run", tmp_path / "base")["unchanged"] == [
        "usage-light-100"]


def test_new_and_missing_surfaces_and_accepting(app, tmp_path):
    _surface(tmp_path / "base", "old-light-100", [])
    _surface(tmp_path / "run", "fresh-light-100", [])
    (tmp_path / "run" / "manifest-light-100.json").write_text("{}", encoding="utf-8")
    result = ui_compare.compare(tmp_path / "run", tmp_path / "base")
    assert result["new"] == ["fresh-light-100"] and result["missing"] == ["old-light-100"]
    assert "## New (no baseline yet)" in ui_compare.report(result)
    assert ui_compare.main([str(tmp_path / "run"), "--baseline", str(tmp_path / "base")]) == 1
    assert (tmp_path / "run" / "compare.md").exists()
    assert ui_compare.main([str(tmp_path / "run"), "--baseline", str(tmp_path / "base"),
                            "--accept", "fresh-light-100"]) == 0
    assert (tmp_path / "base" / "fresh-light-100.png").exists()
    assert not (tmp_path / "base" / "manifest-light-100.json").exists()


def test_a_run_of_one_variant_is_compared_only_with_that_variant(app, tmp_path):
    _surface(tmp_path / "base", "settings-light-100", [])
    _surface(tmp_path / "base", "settings-dark-100", [])
    _surface(tmp_path / "run", "settings-light-100", [])
    (tmp_path / "run" / "manifest-light-100.json").write_text("{}", encoding="utf-8")
    result = ui_compare.compare(tmp_path / "run", tmp_path / "base")
    assert result["missing"] == [] and result["unchanged"] == ["settings-light-100"]


def test_accepting_a_whole_run_keeps_its_manifests(app, tmp_path):
    _surface(tmp_path / "run", "usage-dark-100", [])
    (tmp_path / "run" / "manifest-dark-100.json").write_text('{"tag": "dark-100"}',
                                                              encoding="utf-8")
    assert ui_compare.main([str(tmp_path / "run"), "--baseline", str(tmp_path / "base"),
                            "--accept"]) == 0
    assert (tmp_path / "base" / "manifest-dark-100.json").exists()
    assert (tmp_path / "base" / "usage-dark-100.png").exists()


def test_the_window_border_is_not_compared(app, tmp_path):
    # Windows draws the outer border over whatever is behind the window.
    _surface(tmp_path / "base", "usage-light-150", [], box=(0, 0, 80, 1))
    _surface(tmp_path / "run", "usage-light-150", [], box=(0, 0, 80, 1), colour=(255, 0, 0))
    assert ui_compare.compare(tmp_path / "run", tmp_path / "base")["unchanged"] == [
        "usage-light-150"]
