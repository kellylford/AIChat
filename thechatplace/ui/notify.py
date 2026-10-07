"""Windows notifications (#20), for when The Chat Place isn't the window you're in.

One notification-area icon, The Chat Place's own, created with the first
notification and removed when the app closes. Windows shows its balloons as
ordinary notifications: read by screen readers like any other, and quiet
under Do Not Disturb. A balloon click doesn't say which balloon it was, so
only the latest one's session is kept: choosing it calls ``on_click`` with
that key, and choosing the icon itself calls it with None (just come
forward).

Deliberately not wx's NotificationMessage: it shares a temporary icon whose
hidden window can keep the app running after it closes, and it can send a
click to the wrong notification.
"""
from __future__ import annotations

from typing import Callable, Optional

import wx
import wx.adv

#: Windows' own limits for a balloon's title and text.
TITLE_LIMIT = 63
TEXT_LIMIT = 255


def _fit(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Notifier:
    def __init__(self, on_click: Callable[[Optional[str]], None], tooltip: str,
                 factory=None):
        self._on_click = on_click
        self._tooltip = tooltip
        self._factory = factory or wx.adv.TaskBarIcon
        self._icon = None
        self._key: Optional[str] = None  # the latest notification's session

    def show(self, title: str, message: str, key: str) -> bool:
        try:
            icon = self._ensure_icon()
            shown = bool(icon.ShowBalloon(_fit(title, TITLE_LIMIT),
                                          _fit(message or title, TEXT_LIMIT), 0,
                                          wx.ICON_INFORMATION))
        except Exception:  # noqa: BLE001 - a notification must never break the app
            return False
        if shown:
            self._key = key
        return shown

    def close(self):
        """Remove the icon, and with it our notifications: the app is
        closing, and an icon left behind would keep it running."""
        icon, self._icon, self._key = self._icon, None, None
        if icon is None:
            return
        try:
            icon.RemoveIcon()
            icon.Destroy()
        except Exception:  # noqa: BLE001
            pass

    def _ensure_icon(self):
        if self._icon is None:
            icon = self._factory()
            image = wx.ArtProvider.GetIcon(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
            icon.SetIcon(image, self._tooltip)
            icon.Bind(wx.adv.EVT_TASKBAR_BALLOON_CLICK, self._balloon_clicked)
            icon.Bind(wx.adv.EVT_TASKBAR_LEFT_UP, lambda event: self._on_click(None))
            self._icon = icon
        return self._icon

    def _balloon_clicked(self, _event):
        self._on_click(self._key)
