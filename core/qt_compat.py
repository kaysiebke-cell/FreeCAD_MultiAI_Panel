# -*- coding: utf-8 -*-
"""
Zentrale PySide6/PySide2-Kompatibilitätsweiche.
Alle anderen Module importieren Qt nur noch von hier:

    from qt_compat import QtWidgets, QtCore, QtGui
"""
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    requests = None  # type: ignore[assignment]
    HAS_REQUESTS = False


def single_shot_sicher(ms: int, empfaenger, fn) -> None:
    """QTimer.singleShot, das nicht crasht, wenn das Ziel-Widget beim
    Feuern bereits zerstört wurde ("Internal C++ object already deleted").

    Bevorzugt die Qt-Kontext-Variante: Der Timer wird automatisch
    verworfen, sobald `empfaenger` zerstört wird. Als Fallback (ältere
    Bindings ohne Kontext-Overload) wird ein RuntimeError beim Aufruf
    verschluckt.
    """
    def _sicher():
        try:
            fn()
        except RuntimeError:
            pass  # Widget wurde zwischenzeitlich gelöscht — Timer läuft ins Leere
    try:
        QtCore.QTimer.singleShot(ms, empfaenger, _sicher)
    except TypeError:
        QtCore.QTimer.singleShot(ms, _sicher)


__all__ = ["QtWidgets", "QtCore", "QtGui", "requests", "HAS_REQUESTS",
           "single_shot_sicher"]
