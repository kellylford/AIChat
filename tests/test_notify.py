"""Windows notifications (#20): the Notifier, with a stand-in tray icon."""
import pytest

pytest.importorskip("wx")
import wx  # noqa: E402
import wx.adv  # noqa: E402

from theclaudehub.ui import notify  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return wx.GetApp() or wx.App(False)


class FakeIcon:
    made = []

    def __init__(self):
        self.handlers, self.balloons, self.removed = {}, [], False
        FakeIcon.made.append(self)

    def SetIcon(self, icon, tooltip):
        self.tooltip = tooltip

    def Bind(self, binder, handler):
        self.handlers[binder.typeId] = handler

    def ShowBalloon(self, title, text, msec, flags):
        self.balloons.append((title, text))
        return True

    def RemoveIcon(self):
        self.removed = True

    def Destroy(self):
        pass

    def fire(self, binder):
        self.handlers[binder.typeId](None)


def test_one_icon_the_latest_session_and_removed_on_close(app):
    FakeIcon.made = []
    clicked = []
    notifier = notify.Notifier(clicked.append, "TheClaudeHub", factory=FakeIcon)
    assert notifier.show("Hub probe finished", "All done.", "own:1")
    assert notifier.show("Quiet one needs you", "x" * 400, "local_2")
    assert len(FakeIcon.made) == 1
    icon = FakeIcon.made[0]
    assert icon.tooltip == "TheClaudeHub"
    assert len(icon.balloons[1][1]) == notify.TEXT_LIMIT
    icon.fire(wx.adv.EVT_TASKBAR_BALLOON_CLICK)
    icon.fire(wx.adv.EVT_TASKBAR_LEFT_UP)
    assert clicked == ["local_2", None]
    notifier.close()
    assert icon.removed
    notifier.close()  # twice is fine


def test_a_failing_notification_is_not_an_error(app):
    def broken():
        raise RuntimeError("no notification area")
    assert notify.Notifier(lambda key: None, "x", factory=broken).show("t", "m", "k") is False
