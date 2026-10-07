"""Windows notifications (#20), for when TheClaudeHub isn't the window you're in.

wx's NotificationMessage shows them through a notification-area icon, which
Windows turns into an ordinary notification: it goes to the notification
centre, is read by screen readers like any other, and stays quiet under Do
Not Disturb. Choosing one calls ``on_click`` with the session's key.
"""
from __future__ import annotations

from typing import Callable, List

import wx
import wx.adv

EVT_CLICK = wx.PyEventBinder(wx.adv.wxEVT_NOTIFICATION_MESSAGE_CLICK)
EVT_DISMISSED = wx.PyEventBinder(wx.adv.wxEVT_NOTIFICATION_MESSAGE_DISMISSED)

#: Notifications still showing, at most: older ones are let go.
KEEP = 8


class Notifier:
    def __init__(self, parent: wx.Window, on_click: Callable[[str], None],
                 factory=wx.adv.NotificationMessage):
        self._parent = parent
        self._on_click = on_click
        self._factory = factory
        # A NotificationMessage must outlive its Show(), or Windows has
        # nothing to report the click to.
        self._showing: List[object] = []

    def show(self, title: str, message: str, key: str) -> bool:
        try:
            note = self._factory(title, message, self._parent)
            note.Bind(EVT_CLICK, lambda event: self._clicked(note, key))
            note.Bind(EVT_DISMISSED, lambda event: self._forget(note))
            shown = bool(note.Show())
        except Exception:  # noqa: BLE001 - a notification must never break the app
            return False
        self._showing.append(note)
        del self._showing[:-KEEP]
        return shown

    def _clicked(self, note, key: str):
        self._forget(note)
        self._on_click(key)

    def _forget(self, note):
        if note in self._showing:
            self._showing.remove(note)
