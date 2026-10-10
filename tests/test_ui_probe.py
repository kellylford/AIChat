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


#: wx's own dialogs the probe photographs, which aren't classes of ours.
WX_DIALOGS = {"TextEntryDialog"}


def test_every_dialog_is_photographed_or_says_why_not():
    from thechatplace.ui import dialogs
    classes = {name for name, cls in inspect.getmembers(dialogs, inspect.isclass)
               if issubclass(cls, wx.Dialog) and cls.__module__ == dialogs.__name__}
    covered = set(ui_probe.DIALOG_CLASSES.values()) | set(ui_probe.NOT_PHOTOGRAPHED)
    assert classes - covered == set(), "add a surface to tools/ui_probe.py for these dialogs"
    assert covered - classes == WX_DIALOGS, "the probe names dialogs that no longer exist"


def test_each_dialog_surface_says_which_dialog_it_shows():
    dialog_surfaces = {name for name, (kind, _f, _a) in ui_probe.SURFACES.items()
                       if kind == "dialog"}
    assert dialog_surfaces == set(ui_probe.DIALOG_CLASSES)


@pytest.fixture
def opened(tmp_path, monkeypatch, app):
    """Each surface's setup run on a hidden window, with ShowModal recording
    which dialog would have opened instead of opening it."""
    shown = []

    def record(self):
        shown.append(type(self).__name__)
        return wx.ID_CANCEL
    for cls in (wx.Dialog, wx.TextEntryDialog):
        monkeypatch.setattr(cls, "ShowModal", record)
    return shown


@pytest.mark.parametrize("name", list(ui_probe.SURFACES))
def test_each_surface_opens_what_it_says_on_made_up_data(name, opened, tmp_path, monkeypatch):
    import fake_env
    kind, function, _about = ui_probe.SURFACES[name]
    empty = name in ui_probe.EMPTY_WORLD
    # No web view in the tests: the formatted surfaces expect their plain
    # stand-ins, as on a Mac.
    env = ui_probe.build_world(tmp_path, monkeypatch.setattr, empty=empty, formatted_view=False)
    frame = ui_probe.build_frame(env, empty=empty)
    try:
        if kind == "window":
            assert function(frame, env) is None
            return
        opener = function(frame, env)
        opener()
        assert fake_env.pump(lambda: opened, timeout=10), f"{name} opened no dialog"
        assert opened == [ui_probe.expected_class(name)]
    finally:
        ui_probe.close_frame(frame)


def test_surfaces_start_from_fresh_data(opened, tmp_path, monkeypatch):
    # The working surface leaves a turn running and messages queued; the
    # next surface's window and data are new, so none of that shows there.
    env = ui_probe.build_world(tmp_path / "one", monkeypatch.setattr, formatted_view=False)
    frame = ui_probe.build_frame(env)
    try:
        ui_probe.s_main_own_working(frame, env)
        assert frame._queued
    finally:
        ui_probe.close_frame(frame)
    env = ui_probe.build_world(tmp_path / "two", monkeypatch.setattr, formatted_view=False)
    frame = ui_probe.build_frame(env)
    try:
        assert not frame._queued and not frame._runners
    finally:
        ui_probe.close_frame(frame)


def test_the_plan_names_real_surfaces_and_well_formed_variants():
    plan = json.loads((ROOT / "tools" / "ui_probe_plan.json").read_text(encoding="utf-8"))
    tags = [v["tag"] for v in plan["windows"] + plan["macos"]]
    assert len(tags) == len(set(tags))
    for variant in plan["windows"]:
        assert variant["theme"] in ("light", "dark", "high-contrast")
        assert variant["scale"] in (100, 125, 150, 175, 200)
        assert set(variant.get("surfaces", list(ui_probe.SURFACES))) <= set(list(ui_probe.SURFACES))
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
