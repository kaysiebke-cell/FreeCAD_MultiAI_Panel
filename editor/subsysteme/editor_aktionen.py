# -*- coding: utf-8 -*-
"""
editor_aktionen.py
──────────────────
Zentrale Aktions-Registry des MakroEditors.

Jede Bedien-Aktion existiert genau einmal als QAction (Name, Text,
Shortcut, Callback). Buttons in Toolbar und Docks verbinden sich über
verbinde_button() mit der Aktion — Klick-Verhalten, Shortcut und
Tooltip bleiben so an allen Stellen synchron.
"""

from core.qt_compat import QtWidgets, QtCore, QtGui

# PySide6: QAction lebt in QtGui — PySide2: in QtWidgets
_QAction = getattr(QtGui, "QAction", None) or getattr(QtWidgets, "QAction", None)


class AktionenLogik:
    """Registriert und verwaltet alle QActions des MakroEditors."""

    __slots__ = ("_e", "_aktionen")

    def __init__(self, editor):
        self._e = editor
        self._aktionen = {}
        self._registriere_standard()

    # ── öffentliche API ───────────────────────────────────────────────────

    def registriere(self, name: str, text: str, callback,
                    shortcut: str = "", tooltip: str = ""):
        akt = _QAction(text, self._e)
        if shortcut:
            akt.setShortcut(QtGui.QKeySequence(shortcut))
            akt.setShortcutContext(QtCore.Qt.WindowShortcut)
        akt.setToolTip(self._tooltip_mit_shortcut(tooltip or text, shortcut))
        akt.setStatusTip(tooltip or text)   # Klartext ohne Shortcut-Suffix
        akt.triggered.connect(lambda *_: callback())
        self._e.addAction(akt)   # macht den Shortcut fensterweit aktiv
        self._aktionen[name] = akt
        return akt

    def aktion(self, name: str):
        return self._aktionen[name]

    def verbinde_button(self, name: str, btn: QtWidgets.QPushButton):
        """Verbindet einen QPushButton mit einer Aktion (Klick + Tooltip)."""
        akt = self._aktionen[name]
        btn.clicked.connect(akt.trigger)
        btn.setToolTip(akt.toolTip())
        return btn

    def shortcut_uebersicht(self) -> str:
        """Tastenkürzel-Übersicht für das Hilfe-Panel — generiert aus der
        Registry, bleibt dadurch automatisch synchron zu den Aktionen."""
        zeilen = ["ZENTRALE AKTIONEN (funktionieren überall im Editor)"]
        for akt in self._aktionen.values():
            sc = akt.shortcut().toString()
            if not sc:
                continue
            sc_deutsch = (sc.replace("Ctrl", "Strg")
                            .replace("Shift", "Umsch")
                            .replace("+", " + "))
            zeilen.append(f"  {sc_deutsch:<18}{akt.statusTip()}")
        return "\n".join(zeilen)

    # ── intern ────────────────────────────────────────────────────────────

    @staticmethod
    def _tooltip_mit_shortcut(tooltip: str, shortcut: str) -> str:
        return f"{tooltip}  [{shortcut}]" if shortcut else tooltip

    def _registriere_standard(self):
        e = self._e
        self.registriere("ausfuehren", "▶  Ausführen", e.ausfuehren,
                         "F5", "Speichern und Code in FreeCAD ausführen "
                               "(Ergebnis im FreeCAD-Fenster; während "
                               "eines Laufs: Abbrechen)")
        self.registriere("auswahl_ausfuehren", "▶  Auswahl ausführen",
                         e.auswahl_ausfuehren,
                         "F9", "Nur die markierten Zeilen (oder die aktuelle "
                               "Zeile) in FreeCAD ausführen")
        self.registriere("speichern", "💾  Speichern", e.speichern,
                         "Ctrl+S", "Datei speichern")
        self.registriere("suche", "🔍  Suche", e._toggle_suche,
                         "Ctrl+F", "Suchleiste ein-/ausblenden")
        self.registriere("suche_weiter", "→  Weiter", e._suche_weiter,
                         "F3", "Weiter suchen")
        self.registriere("neu_laden", "↺  Neu laden", e.neu_laden,
                         "Ctrl+Shift+R", "Letzten Speicherstand laden")
        self.registriere("ki_fragen", "🤖  Fragen", e._ki_fragen,
                         "Ctrl+Shift+K", "KI zum Code / Suchfeld befragen")
        self.registriere("formatieren", "✨  Formatieren", e._formatieren,
                         "Ctrl+Shift+F", "Code formatieren")
        self.registriere("hilfe", "❓  Hilfe", e._zeige_hilfe,
                         "F1", "Hilfe und Barrierefreiheit öffnen")
        self.registriere("sprache_zuhoeren", "🎤  Sprache", e._sprache_umschalten,
                         "F4", "Sprachsteuerung: Zuhören starten/stoppen "
                               "(freihändig, ohne Maus)")
