"""Windows notifications (#20): the Notifier, with a stand-in for wx's."""
import pytest

wx = pytest.importorskip("wx")
from theclaudehub.ui import notify  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return wx.GetApp() or wx.App(False)


class FakeNote:
    made = []

    def __init__(self, title, message, parent):
        self.title, self.message, self.handlers = title, message, {}
        FakeNote.made.append(self)

    def Bind(self, binder, handler):
        self.handlers[binder.typeId] = handler

    def Show(self):
        return True

    def click(self):
        self.handlers[notify.EVT_CLICK.typeId](None)

    def dismiss(self):
        self.handlers[notify.EVT_DISMISSED.typeId](None)


def test_click_calls_back_with_the_session_and_old_notes_are_let_go(app):
    clicked = []
    notifier = notify.Notifier(None, clicked.append, factory=FakeNote)
    assert notifier.show("Hub probe finished", "All done.", "own:1")
    note = FakeNote.made[-1]
    assert (note.title, note.message) == ("Hub probe finished", "All done.")
    note.click()
    assert clicked == ["own:1"] and notifier._showing == []
    for i in range(notify.KEEP + 3):
        notifier.show("t", "m", str(i))
    assert len(notifier._showing) == notify.KEEP
    FakeNote.made[-1].dismiss()
    assert len(notifier._showing) == notify.KEEP - 1


def test_a_failing_notification_is_not_an_error(app):
    def broken(*args):
        raise RuntimeError("no notification area")
    assert notify.Notifier(None, lambda key: None, factory=broken).show("t", "m", "k") is False
