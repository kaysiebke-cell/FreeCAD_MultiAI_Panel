# -*- coding: utf-8 -*-
"""
fehler_panel.py
───────────────
FehlerPanel – EINE Fläche: Sandbox-Ausgabe + Fehler-Übersetzung in-place.

Es gibt kein Seiten-Umschalten mehr. Der Fehler steht im Ausgabefeld;
🔍 Übersetzen ersetzt den Text 1:1 durch die deutsche Erklärung (Browser-
Prinzip: gleiches Fenster, Inhalt wird ausgetauscht). Derselbe Button wird
danach zu 🔙 Original und schaltet zurück — ein Button, zwei Zustände.

Der originale (englische) Fehlertext wird separat gemerkt, damit 🔙 Original
zurückkann und 🐛 KI erklärt / 🔧 KI korrigieren stets den echten Fehler
verwenden, nicht die Übersetzung (siehe aktueller_fehlertext()).
"""

from __future__ import annotations
import re
import traceback
from typing import Callable, Dict, Optional
from core.qt_compat import QtWidgets, QtCore, QtGui
from core import theme
from core import schrift

# Erkennt Zeilenangaben in Tracebacks und übersetzten Fehlermeldungen
_ZEILEN_MUSTER = re.compile(r"(?:[Zz]eile|line)\s+(\d+)")


class _KlickbareAusgabe(QtWidgets.QPlainTextEdit):
    """Ausgabefeld: Doppelklick auf eine Zeile mit »Zeile N« / »line N«
    springt über den zeilen_cb-Callback zur Zeile im Editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zeilen_cb: Optional[Callable[[int], None]] = None

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.zeilen_cb is not None:
            block = self.cursorForPosition(event.pos()).block()
            m = _ZEILEN_MUSTER.search(block.text())
            if m:
                self.zeilen_cb(int(m.group(1)))
                return
        super().mouseDoubleClickEvent(event)

# ══════════════════════════════════════════════════════════════════════════════
# Vordefinierte Themes
# ══════════════════════════════════════════════════════════════════════════════

THEME_STANDARD: Dict[str, object] = {
    "bg": "",
    "ausgabe_bg": "",
    "ausgabe_fg": "",
    "ausgabe_border": "",
    "lbl_fg": "",
    "font_family": "Courier New",
    "font_size": 9,
    "lbl_font_size": 9,
    "border_radius": 3,
}


def _merge(base: dict, override: Optional[dict]) -> dict:
    """Mischt override-Werte in base (base bleibt unverändert)."""
    if not override:
        return dict(base)
    return {**base, **override}


def _fix_align(widget: QtWidgets.QPlainTextEdit) -> None:
    opt = widget.document().defaultTextOption()
    opt.setAlignment(QtCore.Qt.AlignLeft)
    widget.document().setDefaultTextOption(opt)


# ══════════════════════════════════════════════════════════════════════════════
# FehlerPanel Klasse
# ══════════════════════════════════════════════════════════════════════════════

class FehlerPanel(QtWidgets.QWidget):
    sandbox_fertig = QtCore.Signal(bool, str)
    # Signal das dem Editor mitteilt wie viel Höhe die Sandbox braucht
    sandbox_hoehe_anfordern = QtCore.Signal(int)

    def __init__(
        self,
        uebersetze_fn: Callable[[str], str],
        ki_callback: Optional[Callable[[], None]] = None,
        theme: Optional[Dict[str, object]] = None,
        max_hoehe: int = 150,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._uebersetze        = uebersetze_fn
        self._ki_cb             = ki_callback
        self._max_h             = max_hoehe
        self._theme             = _merge(THEME_STANDARD, theme)
        self._sandbox_toggle_cb  = None
        self._geladener_code     = ""
        self._korrektur_zaehler  = 0
        self._max_korrekturen    = 3
        self._ki_korrektur_cb    = None   # wird vom Editor gesetzt
        self._laufzeit_check_cb  = None   # wird vom Editor gesetzt (vorschau._vorschau_exec)
        # Übersetzen ⇄ Original (Browser-Prinzip: ein Feld, Inhalt wird getauscht)
        self._zeigt_uebersetzung = False
        self._fehler_original    = ""
        self._baue_ui()

    # ── öffentliche API ───────────────────────────────────────────────────

    def setze_sandbox_toggle_cb(self, cb: Callable[[bool], None]) -> None:
        """Wird vom Editor aufgerufen, um beim Anzeigen den Dock zu öffnen."""
        self._sandbox_toggle_cb = cb

    def aktueller_fehlertext(self) -> str:
        """Der echte (englische) Fehlertext — auch wenn gerade die deutsche
        Übersetzung angezeigt wird. Für KI erklärt / KI korrigieren."""
        if self._zeigt_uebersetzung:
            return self._fehler_original
        return self._sb_ausgabe.toPlainText()

    def sandbox_leeren(self) -> None:
        self._reset_uebersetzung()
        self._sb_ausgabe.clear()
        self._sb_ausgabe.setStyleSheet("")   # Rahmen zurücksetzen
        self._sb_status.clear()
        self._korrektur_zaehler = 0
        self._geladener_code    = ""
        if hasattr(self, "_btn_sb_ki"):
            self._btn_sb_ki.setEnabled(False)
            self._btn_sb_ki.setText("🔧 KI korrigieren")

    def sandbox_setze_code(self, code: str) -> None:
        """Lädt KI-Korrektur-Code – Ausführen muss der User per 🧪 Testen.
        Öffnet den Dock (wie früher zeige_seite(True))."""
        if self._sandbox_toggle_cb:
            self._sandbox_toggle_cb(True)
        self._reset_uebersetzung()
        self._geladener_code = code
        # Zähler NICHT zurücksetzen — KI-Korrekturversuche sollen kumulieren
        verbleibend = self._max_korrekturen - self._korrektur_zaehler
        self._sb_ausgabe.setPlainText("# KI-Korrektur geladen – 🧪 Testen drücken")
        self._sb_status.setText(f"📋 Korrektur bereit – noch {verbleibend}x möglich")
        if hasattr(self, "_btn_sb_ki"):
            self._btn_sb_ki.setEnabled(False)
            self._btn_sb_ki.setText(f"🔧 KI korrigieren ({verbleibend}x)")

    def setze_ki_korrektur_cb(self, cb) -> None:
        """Editor übergibt hier seinen Self-Correction-Callback."""
        self._ki_korrektur_cb = cb

    def setze_laufzeit_check_cb(self, cb) -> None:
        """Editor übergibt hier den FreeCAD-Laufzeit-Check (vorschau._vorschau_exec)."""
        self._laufzeit_check_cb = cb

    def setze_gehe_zu_zeile_cb(self, cb: Callable[[int], None]) -> None:
        """Editor übergibt hier den Sprung-Callback für Doppelklick auf »Zeile N«."""
        self._sb_ausgabe.zeilen_cb = cb

    def _ki_korrektur_anfordern(self) -> None:
        """Schickt den fehlerhaften Code + Fehlermeldung an die KI (max. 3x)."""
        if self._korrektur_zaehler >= self._max_korrekturen:
            self._sb_status.setText(f"❌ Max. {self._max_korrekturen} Korrekturen erreicht")
            self._btn_sb_ki.setEnabled(False)
            return
        if not self._ki_korrektur_cb:
            self._sb_status.setText("⚠ Kein KI-Korrektur-Callback gesetzt")
            return

        fehler_text = self.aktueller_fehlertext()
        code        = self._geladener_code

        if not code or not fehler_text:
            self._sb_status.setText("⚠ Kein Code oder Fehler vorhanden")
            return

        self._korrektur_zaehler += 1
        versuche_text = f"{self._korrektur_zaehler}/{self._max_korrekturen}"
        self._sb_status.setText(f"🔧 KI korrigiert … (Versuch {versuche_text})")
        self._btn_sb_ki.setEnabled(False)

        # Callback im Editor auslösen (der startet den Streaming-Worker)
        self._ki_korrektur_cb(code, fehler_text)

    def sandbox_ausgabe(self) -> str:
        return self._sb_ausgabe.toPlainText()

    def _ki_erklaeren_aus_sandbox(self) -> None:
        """Ein-Klick-Weg vom Fehler zur KI-Erklärung. Der KI-Callback liest
        den Fehler selbst über aktueller_fehlertext() — kein Kopieren nötig."""
        if self._ki_cb is None:
            return
        if not self.aktueller_fehlertext().strip():
            self._sb_status.setText("⚠ Kein Fehler zum Erklären vorhanden")
            return
        self._sb_status.setText("🐛 KI erklärt den Fehler — Antwort im KI-Panel")
        self._ki_cb()

    def ausgabe_starten(self, code: str = "") -> None:
        """Leert das Ausgabefeld für einen neuen Live-Lauf."""
        self._reset_uebersetzung()
        self._sb_ausgabe.clear()
        self._sb_ausgabe.setStyleSheet("")
        self._sb_status.setText("⏳ Läuft …")
        self._geladener_code = code
        self._btn_sb_ki.setEnabled(False)

    def ausgabe_anhaengen(self, text: str) -> None:
        """Hängt eine Zeile an die Ausgabe an ohne den Inhalt zu ersetzen."""
        self._sb_ausgabe.appendPlainText(text)
        sb = self._sb_ausgabe.verticalScrollBar()
        sb.setValue(sb.maximum())

    def setze_theme(self, theme: Dict[str, object]) -> None:
        self._theme = _merge(THEME_STANDARD, theme)
        self._style_anwenden()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────

    def _baue_ui(self) -> None:
        haupt = QtWidgets.QVBoxLayout(self)
        haupt.setContentsMargins(theme.KEIN_RAND, theme.KEIN_RAND,
                                 theme.KEIN_RAND, theme.KEIN_RAND)
        haupt.setSpacing(theme.KEIN_ABSTAND)

        # ── Button-Zeile ──────────────────────────────────────────────────
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(theme.FEHLER_SB_RAND, theme.FEHLER_SB_RAND,
                                      theme.FEHLER_SB_RAND, theme.FEHLER_SB_RAND)
        btn_layout.setSpacing(theme.FEHLER_SB_ABST)

        self._btn_sb_run = QtWidgets.QPushButton("🧪 Testen")
        self._btn_sb_run.setMinimumHeight(theme.FEHLER_SB_BTN_MIN_H)
        self._btn_sb_run.setDefault(True)
        self._btn_sb_run.setAutoDefault(True)
        self._btn_sb_run.setToolTip(
            "KI-Antwort testen: Syntax-Prüfung + Probelauf ohne echte\n"
            "Dokument-Änderungen (Editor-Code direkt ausführen: F5)")
        self._btn_sb_run.clicked.connect(lambda: self._sandbox_ausfuehren())
        btn_layout.addWidget(self._btn_sb_run)

        self._btn_sb_ki = QtWidgets.QPushButton("🔧 KI korrigieren")
        self._btn_sb_ki.setMinimumHeight(theme.FEHLER_SB_BTN_MIN_H)
        self._btn_sb_ki.setAutoDefault(False)
        self._btn_sb_ki.setToolTip("Fehler an KI schicken und korrigierten Code zurückholen (max. 3 Versuche)")
        self._btn_sb_ki.setEnabled(False)
        self._btn_sb_ki.clicked.connect(lambda: self._ki_korrektur_anfordern())
        btn_layout.addWidget(self._btn_sb_ki)

        # 🔍 Übersetzen ⇄ 🔙 Original — ein Button, zwei Zustände
        self._btn_sb_uebersetzen = QtWidgets.QPushButton("🔍 Übersetzen")
        self._btn_sb_uebersetzen.setMinimumHeight(theme.FEHLER_SB_BTN_MIN_H)
        self._btn_sb_uebersetzen.setAutoDefault(False)
        self._btn_sb_uebersetzen.setToolTip(
            "Fehlermeldung ins Deutsche übersetzen — ersetzt den Text 1:1\n"
            "im selben Feld. Erneut klicken: zurück zum Original.")
        self._btn_sb_uebersetzen.clicked.connect(self._uebersetzung_umschalten)
        btn_layout.addWidget(self._btn_sb_uebersetzen)

        self._btn_sb_erklaeren = QtWidgets.QPushButton("🐛 KI erklärt")
        self._btn_sb_erklaeren.setMinimumHeight(theme.FEHLER_SB_BTN_MIN_H)
        self._btn_sb_erklaeren.setAutoDefault(False)
        self._btn_sb_erklaeren.setToolTip(
            "Fehlermeldung von der KI auf Deutsch erklären lassen\n"
            "(ausführliche Antwort im KI-Panel — ändert keinen Code)")
        self._btn_sb_erklaeren.setVisible(self._ki_cb is not None)
        self._btn_sb_erklaeren.clicked.connect(self._ki_erklaeren_aus_sandbox)
        btn_layout.addWidget(self._btn_sb_erklaeren)

        self._btn_sb_clear = QtWidgets.QPushButton("🗑 Leeren")
        self._btn_sb_clear.setMinimumHeight(theme.FEHLER_SB_BTN_MIN_H)
        self._btn_sb_clear.setAutoDefault(False)
        self._btn_sb_clear.clicked.connect(self.sandbox_leeren)
        btn_layout.addWidget(self._btn_sb_clear)

        btn_layout.addStretch()

        self._sb_status = QtWidgets.QLabel("")
        self._sb_status.setStyleSheet(theme.STY_LABEL_SM_NP(schrift.pt(schrift.STUFE_SM)))
        btn_layout.addWidget(self._sb_status)

        haupt.addLayout(btn_layout)

        self._lbl_ausgabe = QtWidgets.QLabel("Ausgabe / Fehler:")
        self._lbl_ausgabe.setStyleSheet(
            theme.STY_LABEL_SM_PADDED(schrift.pt(schrift.STUFE_SM)))
        haupt.addWidget(self._lbl_ausgabe)

        self._sb_ausgabe = _KlickbareAusgabe()
        self._sb_ausgabe.setReadOnly(True)
        self._sb_ausgabe.setToolTip(
            "Doppelklick auf »Zeile N« springt zur Zeile im Editor")
        _fix_align(self._sb_ausgabe)
        self._sb_ausgabe.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        haupt.addWidget(self._sb_ausgabe, stretch=1)

        self.setMinimumHeight(theme.FEHLER_MIN_H)
        self.setMaximumHeight(theme.FEHLER_MAX_H)
        self._style_anwenden()

    # ── Übersetzen ⇄ Original (in-place, ein Feld) ─────────────────────────

    def _reset_uebersetzung(self) -> None:
        """Setzt den Übersetzungs-Zustand zurück — immer wenn frischer Inhalt
        ins Ausgabefeld kommt (neuer Lauf, neuer Fehler, Leeren)."""
        self._zeigt_uebersetzung = False
        self._fehler_original    = ""
        if hasattr(self, "_btn_sb_uebersetzen"):
            self._btn_sb_uebersetzen.setText("🔍 Übersetzen")

    def _uebersetzung_umschalten(self) -> None:
        """🔍 Übersetzen ⇄ 🔙 Original — tauscht den Feldinhalt aus, ohne
        neue Box und ohne Dopplung (Browser-Prinzip)."""
        if self._zeigt_uebersetzung:
            # zurück zum Original
            self._sb_ausgabe.setPlainText(self._fehler_original)
            self._zeigt_uebersetzung = False
            self._btn_sb_uebersetzen.setText("🔍 Übersetzen")
            self._sb_status.setText("↩ Original (Englisch)")
            return
        text = self._sb_ausgabe.toPlainText().strip()
        if not text:
            self._sb_status.setText("⚠ Kein Fehler zum Übersetzen")
            return
        # exakten Inhalt (mit Whitespace) für die Rückkehr merken
        self._fehler_original = self._sb_ausgabe.toPlainText()
        self._sb_ausgabe.setPlainText(self._uebersetze(text))
        self._zeigt_uebersetzung = True
        self._btn_sb_uebersetzen.setText("🔙 Original")
        self._sb_status.setText("🔍 Übersetzt (Deutsch)")

    # ── Sandbox-Ausführung ────────────────────────────────────────────────

    def _sandbox_ausfuehren(self, code: str = None) -> None:
        """Startet Sandbox-Ausführung in eigenem Thread – kein GUI-Freeze."""
        import threading
        if code is None:
            code = getattr(self, "_geladener_code", None)
        if not code or not code.strip():
            self._sb_status.setText("⚠ Kein Code vorhanden – erst per KI generieren")
            return
        code = code.strip()
        self._geladener_code = code
        self._btn_sb_ki.setEnabled(False)
        self._sb_status.setText("⏳ Führe aus …")
        # Fokus auf Ausgabe-Feld parken bevor run deaktiviert wird,
        # damit Qt nicht automatisch zu "Löschen" springt
        self._sb_ausgabe.setFocus()
        self._btn_sb_run.setEnabled(False)
        threading.Thread(target=self._sandbox_worker, args=(code,), daemon=True).start()

    def _sb_rahmen(self, art: str) -> None:
        """Setzt einen farbigen Rahmen um das Ausgabefeld."""
        from core import theme as _theme
        farbe = _theme.farbe_ok(self._sb_ausgabe) if art == "ok" else _theme.farbe_fehler(self._sb_ausgabe)
        self._sb_ausgabe.setStyleSheet(
            f"QPlainTextEdit {{ border: 2px solid {farbe}; border-radius: 3px; }}"
        )

    @QtCore.Slot(bool, str, str)
    def _sandbox_ergebnis(self, erfolg: bool, ausgabe: str, code: str) -> None:
        """Empfängt Ergebnis im GUI-Thread. Frischer Inhalt → Übersetzungs-
        Zustand zurücksetzen (der zeigt sonst noch die alte Übersetzung)."""
        self._btn_sb_run.setEnabled(True)
        self._reset_uebersetzung()
        if erfolg:
            self._sb_ausgabe.setPlainText(ausgabe)
            # Laufzeit-Check direkt im Haupt-Thread anhängen
            if self._laufzeit_check_cb and code.strip():
                rt_fehler = self._laufzeit_check_cb(code)
                if rt_fehler:
                    self._sb_ausgabe.appendPlainText(rt_fehler)
                    self._sb_rahmen("fehler")
                    self._geladener_code = code
                    verbleibend = self._max_korrekturen - self._korrektur_zaehler
                    if verbleibend > 0 and self._ki_korrektur_cb:
                        self._btn_sb_ki.setEnabled(True)
                        self._btn_sb_ki.setText(f"🔧 KI korrigieren ({verbleibend}x)")
                        self._sb_status.setText(f"❌ Laufzeitfehler – KI verfügbar ({verbleibend}x)")
                        self._btn_sb_ki.setFocus()
                    else:
                        self._sb_status.setText("❌ Laufzeitfehler")
                        self._btn_sb_run.setFocus()
                    self.sandbox_fertig.emit(False, rt_fehler)
                    return
            self._sb_status.setText("✅ Erfolgreich ausgeführt")
            self._sb_rahmen("ok")
            self._btn_sb_ki.setEnabled(False)
            self._btn_sb_ki.setText("🔧 KI korrigieren")
            self._korrektur_zaehler = 0
            self.sandbox_fertig.emit(True, ausgabe)
            self._btn_sb_run.setFocus()
        else:
            self._geladener_code = code
            self._sb_ausgabe.setPlainText(ausgabe)
            self._sb_rahmen("fehler")
            verbleibend = self._max_korrekturen - self._korrektur_zaehler
            if verbleibend > 0 and self._ki_korrektur_cb:
                self._btn_sb_ki.setEnabled(True)
                self._btn_sb_ki.setText(f"🔧 KI korrigieren ({verbleibend}x)")
                self._sb_status.setText(f"❌ Fehler – KI verfügbar ({verbleibend}x)")
                # Fokus auf KI-korrigieren — das ist die sinnvolle nächste Aktion
                self._btn_sb_ki.setFocus()
            else:
                self._sb_status.setText("❌ Fehler")
                self._btn_sb_run.setFocus()
            self.sandbox_fertig.emit(False, ausgabe)

    def _sandbox_worker(self, code: str) -> None:
        """Läuft im Hintergrund-Thread – kein GUI-Zugriff."""
        try:
            result  = self._execute_in_sandbox(code)
            erfolg  = result["success"]
            ausgabe = result["output"] if erfolg else result["error"]
        except Exception as e:
            erfolg  = False
            ausgabe = f"Fehler: {e}\n{traceback.format_exc()}"
        QtCore.QMetaObject.invokeMethod(
            self, "_sandbox_ergebnis",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(bool, erfolg),
            QtCore.Q_ARG(str, ausgabe),
            QtCore.Q_ARG(str, code),
        )

    @staticmethod
    def _execute_in_sandbox(code: str) -> Dict:
        """Syntaxprüfung — kein exec(), da FreeCAD nicht in der Sandbox verfügbar."""
        import ast
        code = code.replace("PySide2", "PySide6")
        code = code.replace("from distutils", "# from distutils")
        try:
            ast.parse(code)
            return {"success": True, "output": "✅ Syntax korrekt"}
        except SyntaxError as e:
            return {"success": False, "error": f"Syntax-Fehler Zeile {e.lineno}: {e.msg}"}

    # ── Styling ───────────────────────────────────────────────────────────

    def _style_anwenden(self) -> None:
        # Farben/Schrift kommen zentral aus core/theme + core/schrift;
        # hier bleibt bewusst nichts Hartkodiertes.
        pass
