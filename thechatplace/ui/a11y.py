"""Screen reader naming helpers (from Image Description Toolkit's chat app)."""
from __future__ import annotations

import wx

from . import mac_a11y


class _NamedAccessible(wx.Accessible):
    """Give a text control a name that reaches MSAA.

    childId 0 is the control itself; children (list items) defer to wx so a
    screen reader reads the item, not the control's label, on every arrow.
    """

    def __init__(self, window: wx.Window, label: str):
        super().__init__(window)
        self._label = label

    def set_label(self, label: str) -> None:
        self._label = label

    def GetName(self, childId):
        if childId:
            return (wx.ACC_NOT_IMPLEMENTED, "")
        return (wx.ACC_OK, self._label)


def set_accessible_name(control: wx.Window, label: str) -> None:
    """Name a control for JAWS and NVDA.

    ``SetName`` covers most controls. Text controls also get a wx.Accessible,
    because their name does not otherwise reach MSAA. List boxes don't get
    one here: the messages list has its own (``set_list_items_accessible``),
    which keeps the list's name and its rows' text.

    On macOS neither reaches VoiceOver, so the name goes on the native view
    as well (``mac_a11y``).
    """
    control.SetName(label)
    mac_a11y.set_label(control, label)
    if not isinstance(control, wx.TextCtrl):
        return
    existing = getattr(control, "_hub_accessible", None)
    if existing is not None:
        existing.set_label(label)
        return
    try:
        accessible = _NamedAccessible(control, label)
        control.SetAccessible(accessible)
        control._hub_accessible = accessible  # keep it alive
    except (NotImplementedError, AttributeError):
        pass


class ListItemsAccessible(wx.Accessible):
    """A list box whose items tell the screen reader more than they show
    (#11), as Image Description Toolkit's DescriptionListBox does.

    ``name()`` gives the list's own name (it changes: the messages list's
    name says the session and its state). ``item_text(index)`` gives the text
    a screen reader should read for that row, or None for the row's own text.
    Both are asked each time, so the answer follows the list as it changes.
    Everything else (role, state, child count) is left to wx.
    """

    def __init__(self, window: wx.Window, name, item_text):
        super().__init__(window)
        self._name = name
        self._item_text = item_text

    def GetName(self, childId):
        if not childId:
            return (wx.ACC_OK, self._name())
        try:
            text = self._item_text(childId - 1)  # childId is 1-based for items
        except Exception:  # noqa: BLE001 - never break the screen reader
            text = None
        if text:
            return (wx.ACC_OK, text)
        # The row's own text. The name must be a string even here: with None,
        # wxPython can't build the answer and the screen reader gets an error
        # (0x80010105) instead of the row, found reading it from another
        # process the way JAWS and NVDA do.
        return (wx.ACC_NOT_IMPLEMENTED, "")


def set_list_items_accessible(listbox: wx.ListBox, name, item_text) -> None:
    try:
        accessible = ListItemsAccessible(listbox, name, item_text)
        listbox.SetAccessible(accessible)
        listbox._hub_accessible = accessible  # keep it alive
    except (NotImplementedError, AttributeError):
        pass


def set_voiceover_menu(listbox: wx.ListBox, open_menu) -> None:
    """Open `listbox`'s context menu with VoiceOver's VO+Shift+M, which wx
    doesn't connect to EVT_CONTEXT_MENU on a Mac. ``open_menu()`` is called
    as for the Applications key, with no event, and after VoiceOver's request
    has been answered (see ``mac_a11y.set_show_menu``). Nothing elsewhere."""
    if not mac_a11y.set_show_menu(listbox, lambda: wx.CallAfter(open_menu)):
        return

    def forget(event):
        if event.GetEventObject() is listbox:
            mac_a11y.set_show_menu(listbox, None)
        event.Skip()
    listbox.Bind(wx.EVT_WINDOW_DESTROY, forget)
