# -*- coding: utf-8 -*-
"""Emoji-sichere Schrift-Anwendung: ui_font, mono_font, apply_global_font."""

from core.qt_compat import QtWidgets, QtCore, QtGui
from core import schrift

_FONT_UI_FAMILY   = schrift.FAMILIE_UI
_FONT_MONO_FAMILY = schrift.FAMILIE_MONO
_FONT_UI_SIZE     = schrift.pt(schrift.STUFE_BASE)
_FONT_MONO_SIZE   = schrift.pt(schrift.STUFE_BASE)


def _wrap_emoji(f: QtGui.QFont) -> QtGui.QFont:
    try:
        from main import emoji_font
        return emoji_font(f)
    except Exception:
        return f


def ui_font() -> QtGui.QFont:
    """Gibt die Standard-UI-Schrift zurück, fluid-skaliert, Emoji-sicher."""
    return _wrap_emoji(schrift.ui_font())


def mono_font() -> QtGui.QFont:
    """Gibt die Monospace-Schrift zurück, fluid-skaliert, Emoji-sicher."""
    return _wrap_emoji(schrift.mono_font())


def apply_global_font(widget: QtWidgets.QWidget) -> None:
    """Setzt die UI-Schrift auf das Widget. Im Konstruktor als erstes aufrufen."""
    widget.setFont(ui_font())






