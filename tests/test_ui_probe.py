"""The visual probe (#155) without taking any pictures: it still covers
every dialog, its plan names real surfaces, and its layout checks find
cut-off text and overlapping controls."""
import inspect
import json
import sys
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import ui_probe  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = wx.App(False)
    yield instance


def test_every_dialog_is_photographed_or_says_why_not():
    from thechatplace.ui import dialogs
    classes = {name for name, cls in inspect.getmembers(dialogs, inspect.isclass)
               if issubclass(cls, wx.Dialog) and cls.__module__ == dialogs.__name__}
    covered = set(ui_probe.DIALOG_CLASSES.values()) | set(ui_probe.NOT_PHOTOGRAPHED)
    assert classes - covered == set(), "add a surface to tools/ui_probe.py for these dialogs"
    assert covered - classes == set(), "the probe names dialogs that no longer exist"


def test_each_dialog_surface_says_which_dialog_it_shows():
    dialog_surfaces = {name for name, (kind, _f, _a) in ui_probe.SURFACES.items()
                       if kind == "dialog"}
    # The plain message box is wx's own, so it has no class of ours to check.
    assert dialog_surfaces - set(ui_probe.DIALOG_CLASSES) == {"rename", "message-box"}


def test_the_plan_names_real_surfaces_and_well_formed_variants():
    plan = json.loads((ROOT / "tools" / "ui_probe_plan.json").read_text(encoding="utf-8"))
    tags = [v["tag"] for v in plan["windows"] + plan["macos"]]
    assert len(tags) == len(set(tags))
    for variant in plan["windows"]:
        assert variant["theme"] in ("light", "dark", "high-contrast")
        assert variant["scale"] in (100, 125, 150, 175, 200)
        assert set(variant.get("surfaces", ui_probe.ALL_NAMES)) <= set(ui_probe.ALL_NAMES)
    for variant in plan["macos"]:
        assert variant["theme"] in ("light", "dark")


def _control(entries, label):
    return next(e for e in entries["controls"] if e["label"] == label)


def test_describe_flags_cut_off_text_and_overlaps(app):
    dialog = wx.Dialog(None, title="Probe check", size=(400, 300))
    try:
        cramped = wx.StaticText(dialog, label="A label far too long for the room it was given",
                                pos=(10, 10), size=(60, 20))
        roomy = wx.StaticText(dialog, label="Fits", pos=(10, 60))
        wx.Button(dialog, label="First", pos=(10, 120), size=(100, 30))
        wx.Button(dialog, label="Second", pos=(50, 125), size=(100, 30))
        roomy.SetSize(roomy.GetBestSize())
        assert cramped.GetSize().width == 60
        info = ui_probe.describe(dialog)
        assert info["title"] == "Probe check"
        assert any("text cut off" in p for p in _control(info, cramped.GetLabel())["problems"])
        assert _control(info, "Fits")["problems"] == []
        assert any("overlaps" in p for p in _control(info, "First")["problems"])
    finally:
        dialog.Destroy()


def test_describe_lists_list_items_and_text(app):
    dialog = wx.Dialog(None, title="Lists", size=(400, 300))
    try:
        wx.ListBox(dialog, choices=["one", "two"], pos=(0, 0), size=(100, 100),
                   name="sessions").SetSelection(1)
        wx.TextCtrl(dialog, value="typed", pos=(0, 150), size=(100, 25))
        info = ui_probe.describe(dialog)
        listbox = next(c for c in info["controls"] if c["class"] == "ListBox")
        assert listbox["items"] == ["one", "two"] and listbox["selection"] == 1
        assert next(c for c in info["controls"] if c["class"] == "TextCtrl")["value"] == "typed"
    finally:
        dialog.Destroy()


def test_a_blank_capture_is_recognised(app):
    blank = wx.Bitmap(50, 40)
    dc = wx.MemoryDC(blank)
    dc.SetBackground(wx.WHITE_BRUSH)
    dc.Clear()
    dc.SelectObject(wx.NullBitmap)
    assert ui_probe._one_colour(blank)
    drawn = wx.Bitmap(50, 40)
    dc = wx.MemoryDC(drawn)
    dc.SetBackground(wx.WHITE_BRUSH)
    dc.Clear()
    dc.SetBrush(wx.BLACK_BRUSH)
    dc.DrawRectangle(5, 5, 30, 20)
    dc.SelectObject(wx.NullBitmap)
    assert not ui_probe._one_colour(drawn)
