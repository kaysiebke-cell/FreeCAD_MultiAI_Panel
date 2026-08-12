# -*- coding: utf-8 -*-
"""
conftest.py
───────────
Sammel-Regeln für pytest.

test_editor_live.py startet echte Qt-Widgets und importiert PySide6 bzw.
PySide2 schon beim Laden der Datei. Auf Rechnern ohne Qt — etwa dem
GitHub-Actions-Runner — bricht pytest deshalb bereits beim Einsammeln der
Tests ab, bevor ein einziger Test läuft.

Fehlt Qt, wird die Datei hier übersprungen. Die Qt-freien Tests in
test_back_funktionen.py laufen davon unberührt weiter.
"""

collect_ignore = []

try:
    import PySide6  # noqa: F401
except ImportError:
    try:
        import PySide2  # noqa: F401
    except ImportError:
        collect_ignore.append("test_editor_live.py")
