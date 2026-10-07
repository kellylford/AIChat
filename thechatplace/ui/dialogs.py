"""The Chat Place's dialogs: New Session, Settings, Keyboard Shortcuts."""
from __future__ import annotations

import dataclasses
import os

import wx

from ..changes import file_text
from ..claude_cli import DEFAULT_PERMISSION_MODE, MODELS, PERMISSION_MODES
from ..speech import (ANNOUNCE_LABELS, ANNOUNCE_LEVELS, NOTIFY_LABELS, NOTIFY_LEVELS, RATE_PRESET_LABELS,
                      SpeechSettings)
from ..ui_text import shortcuts_text
from .a11y import set_accessible_name
from .notify import SETTING_LABEL as NOTIFY_SETTING_LABEL, SETTING_NAME as NOTIFY_SETTING_NAME


class ShortcutsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Keyboard Shortcuts", size=(620, 520),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Shortcuts:"), 0, wx.LEFT | wx.TOP, 8)
        text = wx.TextCtrl(self, value=shortcuts_text(),
                           style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        set_accessible_name(text, "Keyboard shortcuts")
        sizer.Add(text, 1, wx.EXPAND | wx.ALL, 8)
        close = wx.Button(self, wx.ID_CANCEL, "&Close")
        close.SetDefault()
        sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        wx.CallAfter(text.SetFocus)


PERMISSION_NOTE = (
    "The permission mode decides what Claude may do without asking. When Claude "
    "asks for permission, asks you a question or has a plan for you to approve, "
    "the turn waits: The Chat Place announces it, the session shows as needing "
    "you, and Ctrl+Shift+A answers.")


CONTINUE_NOTE = (
    "This starts a Chat Place session that is a copy of the desktop app session, "
    "with its whole conversation so far, so you can carry on and reply here. The "
    "desktop app session isn't changed, and replies here don't appear in it.")


class NewSessionDialog(wx.Dialog):
    """Folder, title, model, permission mode, first message.

    With ``continue_from`` (a desktop session's title, #189) it continues that
    session as a copy: the folder is the session's own and can't be changed,
    and the title starts as "<title> (continued)".
    """

    def __init__(self, parent, default_folder: str, continue_from: str = ""):
        title = f"Continue Here: {continue_from}" if continue_from \
            else "New Chat Place Session"
        super().__init__(parent, title=title, size=(640, 560),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.continuing = bool(continue_from)
        outer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self, label="&Folder:"), 0, wx.ALIGN_CENTER_VERTICAL)
        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        self.folder = wx.TextCtrl(self, value=default_folder,
                                  style=wx.TE_READONLY if continue_from else 0)
        set_accessible_name(self.folder, "Folder")
        folder_row.Add(self.folder, 1, wx.EXPAND | wx.RIGHT, 6)
        browse = wx.Button(self, label="&Browse...")
        folder_row.Add(browse, 0)
        browse.Show(not continue_from)
        grid.Add(folder_row, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="&Title:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.title_text = wx.TextCtrl(self, value=f"{continue_from} (continued)"
                                      if continue_from else "")
        set_accessible_name(self.title_text, "Title (optional)")
        grid.Add(self.title_text, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Mo&del:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.model = wx.Choice(self, choices=[label for _v, label in MODELS])
        set_accessible_name(self.model, "Model")
        self.model.SetSelection(0)  # Claude Code's own default
        grid.Add(self.model, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Permission m&ode:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.mode = wx.Choice(self, choices=[label for _v, label in PERMISSION_MODES])
        set_accessible_name(self.mode, "Permission mode")
        values = [v for v, _l in PERMISSION_MODES]
        self.mode.SetSelection(values.index(DEFAULT_PERMISSION_MODE))
        grid.Add(self.mode, 1, wx.EXPAND)
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        # A read-only text box rather than a static label, so it is in the tab
        # order and a screen reader reaches it.
        about = "About continuing" if continue_from else "About permissions"
        outer.Add(wx.StaticText(self, label=f"{about.replace('About ', 'About &')}:"),
                  0, wx.LEFT, 10)
        note = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
                           value=(CONTINUE_NOTE + "\n\n" + PERMISSION_NOTE) if continue_from
                           else PERMISSION_NOTE)
        set_accessible_name(note, about)
        note.SetMinSize((-1, 60))
        outer.Add(note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        outer.Add(wx.StaticText(self, label="First &message:"), 0, wx.LEFT | wx.TOP, 10)
        self.message = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_RICH2)
        set_accessible_name(self.message, "First message")
        outer.Add(self.message, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, "&Start")
        ok.SetDefault()
        buttons.AddButton(ok)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL))
        buttons.Realize()
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)

        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        # Continuing, the folder is fixed: start at the first thing to type.
        wx.CallAfter((self.message if continue_from else self.folder).SetFocus)

    def _on_char_hook(self, event):
        # Ctrl+Enter starts the session from anywhere, as Send does elsewhere.
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and event.ControlDown():
            self._on_ok(None)
            return
        event.Skip()

    def _on_browse(self, _event):
        start = self.folder.GetValue().strip()
        with wx.DirDialog(self, "Choose the folder Claude works in",
                          defaultPath=start if os.path.isdir(start) else "",
                          style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.folder.SetValue(dlg.GetPath())
        self.folder.SetFocus()

    def _on_ok(self, _event):
        folder = self.folder.GetValue().strip()
        if not folder or not os.path.isdir(folder):
            wx.MessageBox("That folder doesn't exist. Choose an existing folder.",
                          "New Session", wx.OK | wx.ICON_WARNING, self)
            self.folder.SetFocus()
            return
        if not self.message.GetValue().strip():
            wx.MessageBox("Type the first message for Claude.", "New Session",
                          wx.OK | wx.ICON_WARNING, self)
            self.message.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def values(self):
        folder = os.path.abspath(self.folder.GetValue().strip())
        message = self.message.GetValue().strip()
        title = " ".join(self.title_text.GetValue().split())
        if not title:
            words = message.split()
            title = " ".join(words[:8]) + ("…" if len(words) > 8 else "")
        index = self.mode.GetSelection()
        mode = PERMISSION_MODES[index][0] if 0 <= index < len(PERMISSION_MODES) \
            else DEFAULT_PERMISSION_MODE
        index = self.model.GetSelection()
        model = MODELS[index][0] if 0 <= index < len(MODELS) else ""
        return folder, title, mode, message, model


class SettingsDialog(wx.Dialog):
    """Announcements and speech (the Speech tab of IDT's settings, adapted)."""

    def __init__(self, parent, speech: SpeechSettings, options):
        super().__init__(parent, title="Settings", size=(680, 580))
        self._options = list(options)
        # Settings kept elsewhere (the session list's sort order) pass through.
        self._original = speech
        outer = wx.BoxSizer(wx.VERTICAL)

        self.level = wx.RadioBox(
            self, label="Announcements",
            choices=[ANNOUNCE_LABELS[level] for level in ANNOUNCE_LEVELS],
            majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.level.SetSelection(ANNOUNCE_LEVELS.index(speech.announce)
                                if speech.announce in ANNOUNCE_LEVELS else 0)
        outer.Add(self.level, 0, wx.EXPAND | wx.ALL, 10)

        self.all_sessions = wx.CheckBox(
            self, label="Announce when &any listed session finishes a turn, "
                        "not just the open one")
        self.all_sessions.SetValue(speech.announce_all_sessions)
        outer.Add(self.all_sessions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.own_messages = wx.CheckBox(
            self, label="Read your own &messages back when they're sent")
        self.own_messages.SetValue(speech.announce_own)
        outer.Add(self.own_messages, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # What you read, apart from what's spoken on its own.
        # Siblings of the group box on purpose (see QuestionDialog); wx's note
        # about that is kept out of the log.
        with wx.LogNull():
            messages = wx.StaticBoxSizer(wx.VERTICAL, self, "Reading messages")
            self.formatted = wx.CheckBox(
                self, label="Open full messages as a formatted &page (headings, lists and "
                           "tables), not plain text")
            self.formatted.SetValue(speech.formatted_messages)
            messages.Add(self.formatted, 0, wx.ALL, 6)
            self.whole_in_list = wx.CheckBox(
                self, label="Read the &whole message on each item in the messages list "
                           "(otherwise just its first line)")
            self.whole_in_list.SetValue(speech.full_messages_in_list)
            messages.Add(self.whole_in_list, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        outer.Add(messages, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, label="Speech &engine:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.engine_choice = wx.Choice(self, choices=[o.label for o in self._options])
        set_accessible_name(self.engine_choice, "Speech engine")
        grid.Add(self.engine_choice, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label="Speaking &rate:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.rate_choice = wx.Choice(
            self, choices=[label.capitalize() for label in RATE_PRESET_LABELS])
        set_accessible_name(self.rate_choice, "Speaking rate")
        grid.Add(self.rate_choice, 0)
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self.rate_note = wx.StaticText(self, label="")
        outer.Add(self.rate_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        notify_row = wx.BoxSizer(wx.HORIZONTAL)
        notify_row.Add(wx.StaticText(self, label=NOTIFY_SETTING_LABEL), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.notify_choice = wx.Choice(self, choices=[NOTIFY_LABELS[n] for n in NOTIFY_LEVELS])
        set_accessible_name(self.notify_choice, f"{NOTIFY_SETTING_NAME}, while The Chat Place "
                                                "isn't the active window")
        self.notify_choice.SetSelection(NOTIFY_LEVELS.index(speech.notifications)
                                        if speech.notifications in NOTIFY_LEVELS else 0)
        notify_row.Add(self.notify_choice, 0)
        outer.Add(notify_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.remote_control = wx.CheckBox(
            self, label="Turn on Remote &Control for The Chat Place's sessions, so you can "
                        "reach them from claude.ai and other devices. Their conversations "
                        "are copied to claude.ai and kept there. (File, Remote Control "
                        "changes one session.)")
        self.remote_control.SetValue(speech.remote_control)
        outer.Add(self.remote_control, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK)
        ok.SetDefault()
        buttons.AddButton(ok)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL))
        buttons.Realize()
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)

        selected = 0
        for i, option in enumerate(self._options):
            if option.engine == speech.engine and option.voice == speech.voice:
                selected = i
                break
        self.engine_choice.SetSelection(selected)
        try:
            self.rate_choice.SetSelection(RATE_PRESET_LABELS.index(speech.rate_preset))
        except ValueError:
            self.rate_choice.SetSelection(0)
        self.engine_choice.Bind(wx.EVT_CHOICE, lambda e: self._update_rate_state())
        self._update_rate_state()
        wx.CallAfter(self.level.SetFocus)

    def _selected_option(self):
        index = self.engine_choice.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._options):
            return self._options[0]
        return self._options[index]

    def _update_rate_state(self):
        option = self._selected_option()
        self.rate_choice.Enable(option.has_rate)
        if option.is_screen_reader:
            self.rate_note.SetLabel("Voice and rate follow your screen reader's own settings.")
        elif option.has_rate:
            self.rate_note.SetLabel("")
        else:
            self.rate_note.SetLabel("This engine uses its default rate.")
        self.Layout()

    def get_settings(self) -> SpeechSettings:
        option = self._selected_option()
        index = self.rate_choice.GetSelection()
        preset = RATE_PRESET_LABELS[index] if 0 <= index < len(RATE_PRESET_LABELS) else "default"
        level_index = self.level.GetSelection()
        level = ANNOUNCE_LEVELS[level_index] if 0 <= level_index < len(ANNOUNCE_LEVELS) \
            else ANNOUNCE_LEVELS[0]
        return dataclasses.replace(self._original, announce=level,
                                   announce_all_sessions=self.all_sessions.GetValue(),
                                   announce_own=self.own_messages.GetValue(),
                                   engine=option.engine, voice=option.voice,
                                   rate_preset=preset,
                                   formatted_messages=self.formatted.GetValue(),
                                   full_messages_in_list=self.whole_in_list.GetValue(),
                                   notifications=NOTIFY_LEVELS[max(
                                       self.notify_choice.GetSelection(), 0)],
                                   remote_control=self.remote_control.GetValue())


class MessageDialog(wx.Dialog):
    """One message's full text, read-only, to read by line, word and character.

    A RichEdit, like the reply box: checked in the vmtest VM, a RichEdit takes
    its accessible name from the label before it, where a plain multiline
    EDIT reports its contents instead. Escape (or Close) returns to the list,
    on the same message.
    """

    def __init__(self, parent, speaker_label: str, text: str):
        super().__init__(parent, title=f"Message from {speaker_label}"
                         if speaker_label in ("Claude", "You") else speaker_label,
                         size=(720, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = f"{speaker_label} said:" if speaker_label in ("Claude", "You") \
            else f"{speaker_label}:"
        sizer.Add(wx.StaticText(self, label="&" + label), 0, wx.LEFT | wx.TOP, 8)
        self.text = wx.TextCtrl(self, value=text,
                                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        set_accessible_name(self.text, label.rstrip(":"))
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        close = wx.Button(self, wx.ID_CANCEL, "&Close")
        sizer.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.text.SetInsertionPoint(0)
        wx.CallAfter(self.text.SetFocus)


# -- a message as a formatted page (#190) -----------------------------------------------

#: EndModal code for "Read as Plain Text": the caller opens MessageDialog.
ID_PLAIN_TEXT = wx.NewIdRef()

#: Escape is pressed inside the page, where wx never sees it, so a script
#: added to the page posts it back. Added with AddUserScript, which runs
#: whatever the page's Content-Security-Policy says.
_KEY_RELAY = """
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') { e.preventDefault(); window.hub.postMessage('escape'); }
  else if (e.altKey && (e.key === 'p' || e.key === 'P')) {
    e.preventDefault(); window.hub.postMessage('plain'); }
}, true);
"""


def formatted_view_available() -> bool:
    """Whether the Edge WebView2 runtime can show the formatted page."""
    try:
        import wx.html2
        return bool(wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge))
    except Exception:  # noqa: BLE001 - no html2, no runtime: plain text
        return False


def _prepare_webview_data_folder() -> None:
    """WebView2 keeps a profile folder. Its default is beside the program,
    which for an installed copy is the folder Velopack replaces on update, and
    for a source run may be Python's own folder. Put it in local app data
    instead, before the first WebView is made."""
    if os.environ.get("WEBVIEW2_USER_DATA_FOLDER"):
        return
    local = os.environ.get("LOCALAPPDATA")
    if local:
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = os.path.join(local, "TheChatPlace WebView2")


class FormattedMessageDialog(wx.Dialog):
    """One message as a web page: the screen reader's browse mode moves by
    heading, table, list and code block. Escape closes it; Read as Plain Text
    (Alt+P) switches to the text box, to read by character.

    Raises RuntimeError if the WebView can't be made; the caller falls back to
    MessageDialog.
    """

    def __init__(self, parent, title: str, page_html: str):
        import wx.html2
        from .. import platform_paths
        super().__init__(parent, title=title, size=(820, 620),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        _prepare_webview_data_folder()
        self._open_url = platform_paths.open_url
        self._loaded = False
        try:
            self.view = wx.html2.WebView.New(self, backend=wx.html2.WebViewBackendEdge)
        except Exception as exc:  # noqa: BLE001
            self.Destroy()
            raise RuntimeError(f"Couldn't show the formatted page: {exc}") from exc
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.EXPAND | wx.ALL, 4)
        row = wx.BoxSizer(wx.HORIZONTAL)
        plain = wx.Button(self, ID_PLAIN_TEXT, "Read as &Plain Text")
        row.Add(plain, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL, "&Close"), 0)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        plain.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(ID_PLAIN_TEXT))
        try:
            self.view.EnableAccessToDevTools(False)
            self.view.AddScriptMessageHandler("hub")
            self.view.AddUserScript(_KEY_RELAY)
        except Exception:  # noqa: BLE001 - Escape still works from the buttons
            pass
        self.view.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._on_script_message)
        self.view.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, self._on_navigating)
        self.view.Bind(wx.html2.EVT_WEBVIEW_NEWWINDOW, self._on_new_window)
        self.view.Bind(wx.html2.EVT_WEBVIEW_LOADED, self._on_loaded)
        self.view.SetPage(page_html, "")

    def _on_loaded(self, _event):
        if not self._loaded:
            self._loaded = True
            # Into the page, so the screen reader starts reading it.
            self.view.SetFocus()

    def _on_script_message(self, event):
        message = event.GetString()
        if message == "escape":
            wx.CallAfter(self.EndModal, wx.ID_CANCEL)
        elif message == "plain":
            wx.CallAfter(self.EndModal, ID_PLAIN_TEXT)

    def _on_navigating(self, event):
        if not self._loaded:
            return  # the page itself
        # A link: never in here. http, https and mailto go to the browser.
        event.Veto()
        url = event.GetURL()
        if url.lower().startswith(("http:", "https:", "mailto:")):
            self._open_url(url)

    def _on_new_window(self, event):
        url = event.GetURL()
        if url.lower().startswith(("http:", "https:", "mailto:")):
            self._open_url(url)


# -- Claude is waiting for an answer (#187, #188) ---------------------------------------
#
# Shared rules: Escape (Answer Later) closes without answering, so the turn
# keeps waiting and Ctrl+Shift+A comes back to it. Nothing refuses or approves
# by accident: Enter's default button is always the harmless choice.

ALLOW, ALLOW_SESSION, DENY = "allow", "session", "deny"
ID_ALLOW = wx.NewIdRef()
ID_ALLOW_SESSION = wx.NewIdRef()
ID_DENY = wx.NewIdRef()


def _read_only_text(parent, value: str, name: str, min_height: int = 160) -> wx.TextCtrl:
    text = wx.TextCtrl(parent, value=value,
                       style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
    set_accessible_name(text, name)
    text.SetMinSize((-1, min_height))
    text.SetInsertionPoint(0)
    return text


class PermissionDialog(wx.Dialog):
    """Claude wants to use a tool: Allow, Allow for this session, Deny.

    The request is in a read-only box to read by line (the whole command, or
    the file and what would change). Deny is the default button, so a stray
    Enter refuses; a reason typed for Deny goes back to Claude.
    """

    def __init__(self, parent, session_title: str, request):
        super().__init__(parent, title=f"Claude needs permission: {session_title}",
                         size=(700, 540), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.choice = ""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Request:"), 0, wx.LEFT | wx.TOP, 8)
        self.request_text = _read_only_text(self, request.detail(), "Request")
        sizer.Add(self.request_text, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label="&Reason to give Claude if you deny (optional):"),
                  0, wx.LEFT, 8)
        self.reason = wx.TextCtrl(self)
        set_accessible_name(self.reason, "Reason to give Claude if you deny (optional)")
        sizer.Add(self.reason, 0, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        allow = wx.Button(self, ID_ALLOW, "&Allow")
        row.Add(allow, 0, wx.RIGHT, 6)
        session_label = request.allow_for_session_label()
        if session_label:
            self.session_button = wx.Button(self, ID_ALLOW_SESSION, "Allow for this &session")
            # The button says what it does in full to a screen reader.
            self.session_button.SetToolTip(session_label)
            set_accessible_name(self.session_button, session_label)
            row.Add(self.session_button, 0, wx.RIGHT, 6)
        else:
            self.session_button = None
        deny = wx.Button(self, ID_DENY, "&Deny")
        deny.SetDefault()
        row.Add(deny, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL, "Answer &Later"), 0)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        for button_id, choice in ((ID_ALLOW, ALLOW), (ID_ALLOW_SESSION, ALLOW_SESSION),
                                  (ID_DENY, DENY)):
            self.Bind(wx.EVT_BUTTON, lambda e, c=choice: self._choose(c), id=button_id)
        wx.CallAfter(self.request_text.SetFocus)

    def _choose(self, choice: str):
        self.choice = choice
        self.EndModal(wx.ID_OK)

    def reason_text(self) -> str:
        return self.reason.GetValue().strip()


OTHER = "Other"


class QuestionDialog(wx.Dialog):
    """Claude's questions (AskUserQuestion), one group per question: the
    options as radio buttons (check boxes when several may be chosen), each
    with its description, and Other with a text box. Send Answers is the
    default button."""

    def __init__(self, parent, session_title: str, request):
        super().__init__(parent, title=f"Claude asks: {session_title}", size=(700, 560),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._questions = request.questions()
        self._controls = []  # per question: (kind, [controls], other text)
        outer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.ScrolledWindow(self, style=wx.VSCROLL)
        panel.SetScrollRate(0, 20)
        sizer = wx.BoxSizer(wx.VERTICAL)
        first = None
        # wx logs that a box's controls "should be" its children: on purpose
        # they aren't (see below), so that note is kept out of the log.
        with wx.LogNull():
            for number, question in enumerate(self._questions, start=1):
                header = str(question.get("header") or f"Question {number}")
                # The question is the group's label. The options are the group
                # box's siblings, after it and inside its rectangle, as in a
                # classic Windows dialog: that is how JAWS and NVDA find a
                # group's label when Tab moves into it. As the box's children,
                # only the first question was read (the one focus starts in).
                box = wx.StaticBoxSizer(wx.VERTICAL, panel, f"{header}: {question['question']}")
                parent_window = panel
                options = [o for o in question.get("options") or [] if isinstance(o, dict)]
                multi = bool(question.get("multiSelect"))
                controls = []
                for index, option in enumerate(options):
                    label = str(option.get("label") or f"Option {index + 1}")
                    description = str(option.get("description") or "")
                    text = f"{label}: {description}" if description else label
                    if multi:
                        control = wx.CheckBox(parent_window, label=text)
                    else:
                        style = wx.RB_GROUP if index == 0 else 0
                        control = wx.RadioButton(parent_window, label=text, style=style)
                        control.SetValue(False)
                    control._hub_label = label
                    controls.append(control)
                    box.Add(control, 0, wx.ALL, 4)
                    first = first or control
                if multi:
                    other = wx.CheckBox(parent_window, label=f"{OTHER} (type below)")
                else:
                    other = wx.RadioButton(parent_window, label=f"{OTHER} (type below)",
                                           style=0 if controls else wx.RB_GROUP)
                    other.SetValue(False)
                other._hub_label = OTHER
                controls.append(other)
                box.Add(other, 0, wx.ALL, 4)
                other_text = wx.TextCtrl(parent_window)
                set_accessible_name(other_text, f"{header}: your own answer")
                box.Add(other_text, 0, wx.EXPAND | wx.ALL, 4)
                other_text.Bind(wx.EVT_TEXT, lambda e, o=other: o.SetValue(True)
                                if e.GetString().strip() else None)
                self._controls.append(("multi" if multi else "single", controls, other_text))
                sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)
                first = first or other
        panel.SetSizer(sizer)
        outer.Add(panel, 1, wx.EXPAND | wx.ALL, 4)

        row = wx.BoxSizer(wx.HORIZONTAL)
        send = wx.Button(self, wx.ID_OK, "&Send Answers")
        send.SetDefault()
        row.Add(send, 0, wx.RIGHT, 6)
        decline = wx.Button(self, ID_DENY, "&Don't Answer")
        row.Add(decline, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL, "Answer &Later"), 0)
        outer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(outer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.declined = False
        send.Bind(wx.EVT_BUTTON, self._on_send)
        decline.Bind(wx.EVT_BUTTON, self._on_decline)
        self._first = first
        if first is not None:
            # Set as the dialog starts, before it's shown: wx would otherwise
            # give the focus to the last group first, and a screen reader
            # would begin reading the wrong question.
            self.Bind(wx.EVT_INIT_DIALOG, self._on_init_dialog)

    def _on_init_dialog(self, event):
        event.Skip()
        self._first.SetFocus()

    def _on_decline(self, _event):
        self.declined = True
        self.EndModal(wx.ID_OK)

    def _on_send(self, _event):
        for (_kind, _controls, other_text), question in zip(self._controls, self._questions):
            if not self._answer_for(_controls, other_text):
                wx.MessageBox(f"Choose an answer for: {question['question']}",
                              self.GetTitle(), wx.OK | wx.ICON_WARNING, self)
                (_controls[0] if _controls else other_text).SetFocus()
                return
        self.EndModal(wx.ID_OK)

    @staticmethod
    def _answer_for(controls, other_text) -> str:
        chosen = []
        for control in controls:
            if not control.GetValue():
                continue
            if control._hub_label == OTHER:
                typed = " ".join(other_text.GetValue().split())
                if typed:
                    chosen.append(typed)
            else:
                chosen.append(control._hub_label)
        return ", ".join(chosen)

    def answers(self):
        """{question text: answer} as Claude Code expects it; several
        choices are joined with commas."""
        return {question["question"]: self._answer_for(controls, other_text)
                for (_kind, controls, other_text), question
                in zip(self._controls, self._questions)}


class PlanDialog(wx.Dialog):
    """Claude's plan, to read, then Approve (choosing the permission mode to
    carry on in) or Keep Planning with a note. Keep Planning is the default
    button: approving starts real changes, so it needs a deliberate press."""

    def __init__(self, parent, session_title: str, request, modes, default_mode: str):
        super().__init__(parent, title=f"Claude's plan: {session_title}", size=(760, 600),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._modes = list(modes)  # (value, label)
        self.approved = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Plan:"), 0, wx.LEFT | wx.TOP, 8)
        self.plan_text = _read_only_text(self, request.plan() or "(Claude sent no plan text.)",
                                         "Plan", min_height=260)
        sizer.Add(self.plan_text, 1, wx.EXPAND | wx.ALL, 8)

        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, label="If approved, carry on &in:"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.mode = wx.Choice(self, choices=[label for _v, label in self._modes])
        set_accessible_name(self.mode, "If approved, carry on in")
        values = [v for v, _l in self._modes]
        self.mode.SetSelection(values.index(default_mode) if default_mode in values else 0)
        grid.Add(self.mode, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label="&What to change (for Keep Planning):"), 0,
                 wx.ALIGN_CENTER_VERTICAL)
        self.note = wx.TextCtrl(self)
        set_accessible_name(self.note, "What to change (for Keep Planning)")
        grid.Add(self.note, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.formatted_button = None
        if formatted_view_available():
            # The plan as a page, by heading and list (#190); back here after.
            self.formatted_button = wx.Button(self, label="Read &Formatted...")
            row.Add(self.formatted_button, 0, wx.RIGHT, 18)
            self.formatted_button.Bind(wx.EVT_BUTTON, lambda e: self._read_formatted(request))
        approve = wx.Button(self, ID_ALLOW, "&Approve")
        row.Add(approve, 0, wx.RIGHT, 6)
        keep = wx.Button(self, ID_DENY, "&Keep Planning")
        keep.SetDefault()
        row.Add(keep, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL, "Answer &Later"), 0)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        approve.Bind(wx.EVT_BUTTON, lambda e: self._finish(True))
        keep.Bind(wx.EVT_BUTTON, lambda e: self._finish(False))
        wx.CallAfter(self.plan_text.SetFocus)

    def _finish(self, approved: bool):
        self.approved = approved
        self.EndModal(wx.ID_OK)

    def _read_formatted(self, request):
        from ..rendering import message_page
        title = "Claude's plan"
        try:
            dialog = FormattedMessageDialog(self, title, message_page(title, request.plan()))
        except RuntimeError:
            self.plan_text.SetFocus()
            return
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()
        (self.formatted_button or self.plan_text).SetFocus()

    def chosen_mode(self) -> str:
        index = self.mode.GetSelection()
        return self._modes[index][0] if 0 <= index < len(self._modes) else self._modes[0][0]

    def note_text(self) -> str:
        return self.note.GetValue().strip()


class ManageGroupsDialog(wx.Dialog):
    """File, Manage Groups (#31): the groups, each with how many sessions
    it has, and New, Rename, Delete. Changes are saved as they're made;
    Close (or Escape) closes. Deleting a group asks first, and never touches
    its sessions."""

    def __init__(self, parent, groups, counts):
        super().__init__(parent, title="Manage Groups", size=(480, 420),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.groups = groups
        self._counts = dict(counts)
        #: old name -> new name, for every rename made here (chains followed).
        self.renamed = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Groups:"), 0, wx.LEFT | wx.TOP, 8)
        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self.list, "Groups")
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.new_btn = wx.Button(self, label="&New...")
        self.rename_btn = wx.Button(self, label="&Rename...")
        self.delete_btn = wx.Button(self, label="&Delete...")
        for button in (self.new_btn, self.rename_btn, self.delete_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        row.AddStretchSpacer()
        row.Add(wx.Button(self, wx.ID_CANCEL, "&Close"), 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.new_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_new())
        self.rename_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_rename())
        self.delete_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_delete())
        self._fill()
        wx.CallAfter(self.list.SetFocus)

    def _row(self, name: str) -> str:
        count = self._counts.get(name, 0)
        return f"{name}, {count} session{'s' if count != 1 else ''}"

    def _fill(self, select: str = ""):
        names = self.groups.names()
        if names:
            self.list.Set([self._row(n) for n in names])
            self.list.SetSelection(names.index(select) if select in names else 0)
        else:
            self.list.Set(["No groups yet. New makes one."])
            self.list.SetSelection(0)
        # Always enabled, so the Tab order doesn't change; they say if
        # there's nothing to act on.

    def _selected(self):
        names = self.groups.names()
        index = self.list.GetSelection()
        return names[index] if names and 0 <= index < len(names) else None

    def _ask(self, title: str, value: str = ""):
        dialog = wx.TextEntryDialog(self, "Group name:", title, value)
        try:
            return dialog.GetValue() if dialog.ShowModal() == wx.ID_OK else None
        finally:
            dialog.Destroy()

    def _try(self, action):
        try:
            return action()
        except (ValueError, OSError) as exc:
            wx.MessageBox(str(exc), self.GetTitle(), wx.OK | wx.ICON_WARNING, self)
            return None

    def on_new(self):
        name = self._ask("New Group")
        if name is not None:
            made = self._try(lambda: self.groups.create(name))
            if made:
                self._fill(made)
        self.list.SetFocus()

    def on_rename(self):
        old = self._selected()
        if old is None:
            wx.MessageBox("There's no group to rename.", self.GetTitle(),
                          wx.OK | wx.ICON_INFORMATION, self)
        else:
            new = self._ask("Rename Group", old)
            if new is not None:
                renamed = self._try(lambda: self.groups.rename(old, new))
                if renamed:
                    self._counts[renamed] = self._counts.pop(old, 0)
                    for first, latest in list(self.renamed.items()):
                        if latest == old:
                            self.renamed[first] = renamed
                    self.renamed.setdefault(old, renamed)
                    self._fill(renamed)
        self.list.SetFocus()

    def on_delete(self):
        name = self._selected()
        if name is None:
            wx.MessageBox("There's no group to delete.", self.GetTitle(),
                          wx.OK | wx.ICON_INFORMATION, self)
        elif wx.MessageBox(f"Delete the group {name}? Its sessions stay; only the group "
                           "goes.", self.GetTitle(),
                           wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self) == wx.YES:
            self._try(lambda: self.groups.delete(name))
            self._fill()
        self.list.SetFocus()


class CommandPickerDialog(wx.Dialog):
    """File, Insert Command or Skill (#23): Claude Code's slash commands
    and your skills for this folder, yours first. Type to filter by name or
    description; Down moves into the list; Enter (or Insert) chooses."""

    def __init__(self, parent, commands):
        super().__init__(parent, title="Insert Command or Skill", size=(720, 520),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._all = list(commands)
        self._shown = []
        self.chosen = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Search:"), 0, wx.LEFT | wx.TOP, 8)
        self.search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.search, "Search commands and skills")
        sizer.Add(self.search, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.list_label = wx.StaticText(self, label="&Commands and skills:")
        sizer.Add(self.list_label, 0, wx.LEFT | wx.TOP, 8)
        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self.list, "Commands and skills")
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        insert = wx.Button(self, wx.ID_OK, "&Insert")
        insert.SetDefault()
        row.Add(insert, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL), 0)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.search.Bind(wx.EVT_TEXT, lambda e: self._filter())
        self.search.Bind(wx.EVT_TEXT_ENTER, lambda e: self._choose())
        self.search.Bind(wx.EVT_KEY_DOWN, self._on_search_key)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._choose())
        insert.Bind(wx.EVT_BUTTON, lambda e: self._choose())
        self._filter()
        wx.CallAfter(self.search.SetFocus)

    @staticmethod
    def row(command) -> str:
        name = f"/{command['name']}"
        hint = str(command.get("argumentHint") or "").strip()
        text = " ".join(str(command.get("description") or "").split())
        if len(text) > 200:
            text = text[:199] + "…"
        owner = ", Claude Code" if command.get("builtin") else ""
        return f"{name}{' ' + hint if hint else ''}{owner}: {text}" if text else f"{name}{owner}"

    def _filter(self):
        words = self.search.GetValue().lower().split()
        self._shown = [c for c in self._all
                       if all(w in (c["name"] + " " + str(c.get("description") or "")).lower()
                              for w in words)]
        if self._shown:
            self.list.Set([self.row(c) for c in self._shown])
            self.list.SetSelection(0)
        else:
            self.list.Set(["Nothing matches."])
            self.list.SetSelection(0)
        count = len(self._shown)
        self.list_label.SetLabel(f"&Commands and skills ({count} of {len(self._all)}):")
        set_accessible_name(self.list, f"Commands and skills, {count} of {len(self._all)}")

    def _on_search_key(self, event):
        if event.GetKeyCode() in (wx.WXK_DOWN, wx.WXK_UP) and self._shown:
            # Down lands on the first entry (the top one is already chosen by
            # default, so Down from the box shouldn't need pressing twice).
            self.list.SetFocus()
            self.list.SetSelection(0)
            return
        event.Skip()

    def _choose(self):
        index = self.list.GetSelection()
        if not self._shown or not (0 <= index < len(self._shown)):
            wx.Bell()
            return
        self.chosen = self._shown[index]
        self.EndModal(wx.ID_OK)
class BugReportDialog(wx.Dialog):
    """Help, Report a Bug (#28), as QuickMail's: a summary, what happened,
    what you expected and the steps, then what the report will include, to
    read before it goes anywhere. Open on GitHub (the default) copies the
    whole report and opens GitHub's new-issue page with it filled in; Copy
    Report only copies it."""

    def __init__(self, parent, environment_lines):
        super().__init__(parent, title="Report a Bug", size=(660, 640),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.action = ""
        outer = wx.BoxSizer(wx.VERTICAL)

        def field(label, name, multiline=False, height=-1):
            outer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 8)
            style = (wx.TE_MULTILINE | wx.TE_RICH2) if multiline else 0
            control = wx.TextCtrl(self, style=style)
            set_accessible_name(control, name)
            if multiline:
                control.SetMinSize((-1, height))
            outer.Add(control, 1 if multiline else 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
            return control

        self.summary = field("&Summary (the issue's title):", "Summary")
        self.summary.SetMaxLength(200)
        self.happened = field("What &happened:", "What happened", True, 70)
        self.expected = field("What you &expected (optional):", "What you expected (optional)",
                              True, 50)
        self.steps = field("S&teps to reproduce (optional):", "Steps to reproduce", True, 50)
        outer.Add(wx.StaticText(self, label="What the report &includes besides your words "
                                            "(no session titles, folders or messages):"),
                  0, wx.LEFT | wx.TOP, 8)
        self.included = _read_only_text(self, "\n".join(environment_lines),
                                        "What the report includes", min_height=90)
        outer.Add(self.included, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        outer.Add(wx.StaticText(self, label=(
            "Open on GitHub needs access to the app's repository on GitHub. Without it, "
            "use Copy Report and email the report to support@theideaplace.net.")),
            0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.open_btn = wx.Button(self, wx.ID_OK, "&Open on GitHub")
        self.open_btn.SetDefault()
        copy = wx.Button(self, label="&Copy Report")
        row.Add(self.open_btn, 0, wx.RIGHT, 6)
        row.Add(copy, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL), 0)
        outer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(outer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.open_btn.Bind(wx.EVT_BUTTON, lambda e: self._finish("open"))
        copy.Bind(wx.EVT_BUTTON, lambda e: self._finish("copy"))
        wx.CallAfter(self.summary.SetFocus)

    def _finish(self, action: str):
        for control, what in ((self.summary, "a summary"), (self.happened, "what happened")):
            if not control.GetValue().strip():
                wx.MessageBox(f"Please write {what} first.", self.GetTitle(),
                              wx.OK | wx.ICON_INFORMATION, self)
                control.SetFocus()
                return
        self.action = action
        self.EndModal(wx.ID_OK)

    def values(self):
        return (" ".join(self.summary.GetValue().split()), self.happened.GetValue(),
                self.expected.GetValue(), self.steps.GetValue())


class CodeBlocksDialog(wx.Dialog):
    """A message's code blocks (#17): a list ("Python, 14 lines: def main():
    …"), the selected block's code in a read-only box to read by line, word
    and character, and Copy for just that block."""

    def __init__(self, parent, blocks, copy):
        super().__init__(parent, title="Code Blocks", size=(760, 560),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._blocks = list(blocks)
        self._copy = copy
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="Code &blocks:"), 0, wx.LEFT | wx.TOP, 8)
        self.list = wx.ListBox(self, style=wx.LB_SINGLE,
                               choices=[b.row() for b in self._blocks])
        set_accessible_name(self.list, f"Code blocks, {len(self._blocks)}")
        self.list.SetMinSize((-1, 110))
        sizer.Add(self.list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="Co&de:"), 0, wx.LEFT | wx.TOP, 8)
        self.code = _read_only_text(self, "", "Code", min_height=220)
        self.code.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.code, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self, label="&Copy")
        row.Add(copy_btn, 0, wx.RIGHT, 6)
        row.Add(wx.Button(self, wx.ID_CANCEL, "C&lose"), 0)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.list.Bind(wx.EVT_LISTBOX, lambda e: self._show())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self.code.SetFocus())
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        copy_btn.Bind(wx.EVT_BUTTON, lambda e: self.copy_selected())
        if self._blocks:
            self.list.SetSelection(0)
            self._show()
        wx.CallAfter(self.list.SetFocus)

    def _show(self):
        index = self.list.GetSelection()
        if 0 <= index < len(self._blocks):
            block = self._blocks[index]
            self.code.ChangeValue(block.code)
            self.code.SetInsertionPoint(0)
            # Tabbing in says which block this is.
            set_accessible_name(self.code, block.describe())

    def _on_list_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.code.SetFocus()  # Enter: read the block's code
            return
        event.Skip()

    def copy_selected(self):
        index = self.list.GetSelection()
        if 0 <= index < len(self._blocks):
            self._copy(self._blocks[index])


class ChangesDialog(wx.Dialog):
    """The files Claude changed (#18): from your latest message or the whole
    session, each file's line counts, and the selected file's changes to
    read by line ("Removed: …", "Added: …")."""

    def __init__(self, parent, title, latest, everything, describe):
        super().__init__(parent, title=f"Changed Files: {title}", size=(800, 580),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._sets = [latest, everything]
        self._describe = describe
        self._files = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="&Show changes from:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.scope = wx.Choice(self, choices=["Your latest message", "The whole session"])
        set_accessible_name(self.scope, "Show changes from")
        self.scope.SetSelection(0 if latest else 1)
        row.Add(self.scope, 0)
        sizer.Add(row, 0, wx.LEFT | wx.TOP | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="&Files:"), 0, wx.LEFT | wx.TOP, 8)
        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        self.list.SetMinSize((-1, 130))
        sizer.Add(self.list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="C&hanges:"), 0, wx.LEFT | wx.TOP, 8)
        self.text = _read_only_text(self, "", "Changes", min_height=240)
        self.text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                                  wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(wx.Button(self, wx.ID_CANCEL, "C&lose"), 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.scope.Bind(wx.EVT_CHOICE, lambda e: self._fill())
        self.list.Bind(wx.EVT_LISTBOX, lambda e: self._show())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self.text.SetFocus())
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._fill()
        wx.CallAfter(self.list.SetFocus)

    def _fill(self):
        self._files = self._sets[self.scope.GetSelection()]
        rows = [self._describe(f) for f in self._files] or ["No files changed."]
        self.list.Set(rows)
        set_accessible_name(self.list, f"Files, {len(self._files)}")
        self.list.SetSelection(0)
        self._show()

    def _show(self):
        index = self.list.GetSelection()
        if 0 <= index < len(self._files):
            changes = self._files[index]
            self.text.ChangeValue(file_text(changes))
            set_accessible_name(self.text, f"Changes to {os.path.basename(changes.path)}")
        else:
            self.text.ChangeValue("")
            set_accessible_name(self.text, "Changes")
        self.text.SetInsertionPoint(0)

    def _on_list_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.text.SetFocus()  # Enter: read the file's changes
            return
        event.Skip()


class AboutYouDialog(wx.Dialog):
    """What Claude knows about you (#92): your instructions, memories,
    skills, subagents, slash commands, output styles and settings, read from
    Claude Code's own files. A list of kinds, the chosen kind's items, and
    the selected item's file to read by line. The Chat Place only reads them:
    Edit opens the file in your own editor, and Reload shows what changed."""

    def __init__(self, parent, load, edit, show, copy):
        super().__init__(parent, title="What Claude Knows About You", size=(860, 640),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._load, self._edit, self._show_file, self._copy = load, edit, show, copy
        self._kinds = []
        self._items = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=(
            "Read from Claude Code's own files on this computer. The Chat Place only reads "
            "them: Edit opens a file in your editor, and Reload shows your changes.")),
            0, wx.LEFT | wx.TOP | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="&Kind:"), 0, wx.LEFT | wx.TOP, 8)
        self.kinds = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self.kinds, "Kind")
        self.kinds.SetMinSize((-1, 120))
        sizer.Add(self.kinds, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.about = wx.StaticText(self, label="")
        sizer.Add(self.about, 0, wx.LEFT | wx.TOP | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="&Items:"), 0, wx.LEFT | wx.TOP, 8)
        self.items = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self.items, "Items")
        self.items.SetMinSize((-1, 140))
        sizer.Add(self.items, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Locatio&n:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.location = wx.TextCtrl(self, style=wx.TE_READONLY)
        set_accessible_name(self.location, "Location")
        row.Add(self.location, 1)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self, label="C&ontents:"), 0, wx.LEFT | wx.TOP, 8)
        self.text = _read_only_text(self, "", "Contents", min_height=200)
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.edit_btn = wx.Button(self, label="&Edit in Your Editor")
        self.show_btn = wx.Button(self, label="Show in Fol&der")
        self.copy_btn = wx.Button(self, label="Copy &Path")
        reload_btn = wx.Button(self, label="&Reload")
        for button in (self.edit_btn, self.show_btn, self.copy_btn, reload_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self, wx.ID_CANCEL, "C&lose"), 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        self.kinds.Bind(wx.EVT_LISTBOX, lambda e: self._fill_items())
        self.kinds.Bind(wx.EVT_KEY_DOWN, self._on_kinds_key)
        self.items.Bind(wx.EVT_LISTBOX, lambda e: self._show())
        self.items.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self.text.SetFocus())
        self.items.Bind(wx.EVT_KEY_DOWN, self._on_items_key)
        self.edit_btn.Bind(wx.EVT_BUTTON, lambda e: self.edit_selected())
        self.show_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_selected())
        self.copy_btn.Bind(wx.EVT_BUTTON, lambda e: self.copy_selected())
        reload_btn.Bind(wx.EVT_BUTTON, lambda e: self.reload())
        self.reload()
        wx.CallAfter(self.kinds.SetFocus)

    def reload(self):
        """Read everything again, keeping your place where it still exists."""
        kind_index = max(self.kinds.GetSelection(), 0)
        selected = self.selected_item()
        self._kinds = self._load()
        self.kinds.Set([k.row() for k in self._kinds])
        if self._kinds:
            self.kinds.SetSelection(min(kind_index, len(self._kinds) - 1))
        self._fill_items(keep=selected.path if selected is not None else None)

    def _fill_items(self, keep=None):
        index = self.kinds.GetSelection()
        kind = self._kinds[index] if 0 <= index < len(self._kinds) else None
        self._items = list(kind.items) if kind is not None else []
        self.about.SetLabel(kind.about if kind is not None else "")
        self.items.Set([i.row() for i in self._items] or ["Nothing here yet."])
        name = kind.name if kind is not None else "Items"
        set_accessible_name(self.items, f"{name}, {len(self._items)}")
        paths = [i.path for i in self._items]
        self.items.SetSelection(paths.index(keep) if keep in paths else 0)
        self._show()

    def selected_item(self):
        index = self.items.GetSelection() if self._items else -1
        return self._items[index] if 0 <= index < len(self._items) else None

    def _show(self):
        from ..about_you import read_text

        item = self.selected_item()
        for button in (self.edit_btn, self.show_btn, self.copy_btn):
            button.Enable(item is not None)
        if item is None:
            self.location.ChangeValue("")
            self.text.ChangeValue("")
            set_accessible_name(self.text, "Contents")
            return
        try:
            text = read_text(item.path)
        except OSError as exc:
            text = f"Couldn't read this file: {exc}"
        self.location.ChangeValue(str(item.path))
        self.text.ChangeValue(text)
        self.text.SetInsertionPoint(0)
        # Tabbing in says whose file it is.
        set_accessible_name(self.text, f"Contents of {item.name}")

    def _on_kinds_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.items.SetFocus()  # Enter: into the kind's items
            return
        event.Skip()

    def _on_items_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.text.SetFocus()  # Enter: read the file
            return
        event.Skip()

    def edit_selected(self):
        item = self.selected_item()
        if item is None:
            return
        try:
            self._edit(item.path)
        except OSError as exc:
            wx.MessageBox(f"Couldn't open {item.path} in an editor: {exc}",
                          "What Claude Knows About You", wx.OK | wx.ICON_WARNING, self)

    def show_selected(self):
        item = self.selected_item()
        if item is None:
            return
        try:
            self._show_file(item.path)
        except OSError as exc:
            wx.MessageBox(f"Couldn't show {item.path}: {exc}",
                          "What Claude Knows About You", wx.OK | wx.ICON_WARNING, self)

    def copy_selected(self):
        item = self.selected_item()
        if item is not None:
            self._copy(str(item.path))
