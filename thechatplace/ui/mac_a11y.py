"""Name controls for VoiceOver, which wx can't do on macOS (from Image
Description Toolkit's shared/mac_accessibility.py), and make the app active
so VoiceOver finds its menu bar (``activate_app``).

Measured on wxPython 4.3.1 / wxWidgets 3.3.3: ``SetAccessible()`` raises
``NotImplementedError`` (``wx.Accessible`` is Windows-only), and ``SetName()``
reaches nothing native. Every ``wx.TextCtrl``, ``wx.ListBox`` and ``wx.Choice``
reports ``accessibilityLabel == nil`` however it was named, so VoiceOver read
an edit box's contents and never its label. Buttons and check boxes are fine
without help: AppKit names them from their title.

So the label is set on the native view through NSAccessibility, with ctypes
rather than PyObjC, which isn't a dependency and would be a lot to add to the
app bundle for three selectors.

``GetHandle()`` isn't always the view VoiceOver lands on. A multi-line
``wx.TextCtrl`` is a scroll view around an ``NSTextView``, and a ``wx.ListBox``
a scroll view around an ``NSTableView``. VoiceOver focuses the inner view, so
when the handle has a ``documentView``, that is what gets the label.

This module doesn't import wx, so its logic can be tested anywhere, and
everything in it is a no-op off macOS.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import sys

IS_MACOS = sys.platform == "darwin"

_objc = None  # the loaded libobjc, or False once loading has failed


def _runtime():
    """The Objective-C runtime, or None where it is unavailable."""
    global _objc
    if _objc is None:
        _objc = False
        if IS_MACOS:
            try:
                path = ctypes.util.find_library("objc")
                lib = ctypes.cdll.LoadLibrary(path) if path else None
            except OSError:
                lib = None
            if lib is not None:
                lib.sel_registerName.restype = ctypes.c_void_p
                lib.sel_registerName.argtypes = [ctypes.c_char_p]
                lib.objc_getClass.restype = ctypes.c_void_p
                lib.objc_getClass.argtypes = [ctypes.c_char_p]
                _objc = lib
    return _objc or None


def _send(obj, selector, *args, restype=ctypes.c_void_p, argtypes=()):
    """``[obj selector:args]``.

    objc_msgSend is cast to each method's own prototype: calling it through
    the wrong one is undefined on arm64.
    """
    objc = _runtime()
    signature = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)
    call = signature(ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value)
    return call(obj, objc.sel_registerName(selector.encode()), *args)


def _responds(obj, selector) -> bool:
    objc = _runtime()
    return bool(_send(obj, "respondsToSelector:",
                      ctypes.c_void_p(objc.sel_registerName(selector.encode())),
                      restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,)))


def _nsstring(text: str):
    objc = _runtime()
    return _send(objc.objc_getClass(b"NSString"), "stringWithUTF8String:",
                 text.encode("utf-8"), argtypes=(ctypes.c_char_p,))


def _to_str(nsstring) -> str | None:
    if not nsstring:
        return None
    pointer = _send(nsstring, "UTF8String", restype=ctypes.c_char_p)
    return pointer.decode("utf-8") if pointer else None


def _target_view(window):
    """The native view VoiceOver focuses for `window`, or None."""
    if _runtime() is None:
        return None
    try:
        handle = window.GetHandle()
    except (AttributeError, RuntimeError):
        return None
    if not handle:
        return None
    view = ctypes.c_void_p(handle)
    if _responds(view, "documentView"):
        inner = _send(view, "documentView")
        if inner:
            return ctypes.c_void_p(inner)
    return view


def set_label(window, label: str) -> bool:
    """Give `window` the name VoiceOver reads. True if it was applied.

    False, never an exception, off macOS or on a control with no native view:
    a missing name mustn't take the window down with it.
    """
    if not IS_MACOS or not label:
        return False
    try:
        view = _target_view(window)
        if view is None or not _responds(view, "setAccessibilityLabel:"):
            return False
        _send(view, "setAccessibilityLabel:", ctypes.c_void_p(_nsstring(label)),
              argtypes=(ctypes.c_void_p,))
        return True
    except Exception:  # noqa: BLE001 - never break the window over a name
        return False


def activate_app() -> bool:
    """Make The Chat Place the active app. True if it was asked to.

    VO+M opens the active app's menu bar, and a wx window can be in front
    without its app being active: ``Raise()`` only orders the window front,
    and a copy started from a terminal (``python -m thechatplace``, or the
    bare program in ``dist/TheChatPlace/``) isn't activated by macOS the way
    a double-clicked .app is. Then VO+M went to the menus of the app used
    before, the Claude desktop app.
    """
    if not IS_MACOS or _runtime() is None:
        return False
    try:
        app = _send(_runtime().objc_getClass(b"NSApplication"), "sharedApplication")
        if not app:
            return False
        _send(ctypes.c_void_p(app), "activateIgnoringOtherApps:", True,
              restype=None, argtypes=(ctypes.c_bool,))
        return True
    except Exception:  # noqa: BLE001
        return False


def get_label(window) -> str | None:
    """The name VoiceOver would read for `window`, or None. For tests, and for
    checking a control reported as unlabelled."""
    if not IS_MACOS:
        return None
    try:
        view = _target_view(window)
        if view is None or not _responds(view, "accessibilityLabel"):
            return None
        return _to_str(_send(view, "accessibilityLabel"))
    except Exception:  # noqa: BLE001
        return None
