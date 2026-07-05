# -*- coding: utf-8 -*-
"""
sprach_panel.py  (PROTOTYP)
───────────────────────────
Barrierefreies Sprach-Panel: EINMAL klicken → sprechen → stoppt von selbst
bei der Sprechpause (kein Halten einer Taste). Optional Freihand-Modus, der
nach jedem Befehl weiter zuhört. Erkannter Text → registrierte Aktion.

Nutzt vom Editor:
  _aktionen     (AktionenLogik-Registry — Ziel der Sprachbefehle)
  _set_status() (visuelle Rückmeldung in der Statuszeile)
"""

from __future__ import annotations

from core.qt_compat import QtWidgets, QtCore

from editor.sprache.sprach_kern import (
    BefehlsGrammatik, SprachWorker, ModellLader, sprich, _normalisieren,
    HAS_VOSK, finde_vosk_modell, aufnahme_moeglich,
)

# ── Panels per Sprache öffnen ────────────────────────────────────────────────
_L = QtCore.Qt.LeftDockWidgetArea
_R = QtCore.Qt.RightDockWidgetArea
_B = QtCore.Qt.BottomDockWidgetArea

# Erfordert ein „Öffnen"-Verb, damit Panelnamen nicht mit Aktionen kollidieren
# (z. B. „hilfe" = Aktion, aber „öffne hilfe" = Panel).
# Wortstämme (startet-mit) — robust gegen Schreib-/Erkennungsvarianten
# (schließe / schliese / schliesse / schließen … treffen alle über "schlie")
_OEFFNEN_STAEMME    = ("öffn", "zeig", "aufmach", "wechsl", "panel", "geh")
_SCHLIESSEN_STAEMME = ("schlie", "zumach", "verberg", "ausblend", "blend", "weg")
_STOP_WORTE        = ("stop", "stopp", "halt", "anhalten", "abbrechen", "abbruch", "abbrich")
_UNDO_WORTE        = ("rückgängig", "widerrufen", "zurücknehmen", "undo")

# ── Diktat ───────────────────────────────────────────────────────────────────
# Gesprochene Satzzeichen/Steuerwörter (ganze Äußerung == Schlüssel)
_SATZZEICHEN = {
    "punkt": ".", "komma": ",", "fragezeichen": "?", "ausrufezeichen": "!",
    "doppelpunkt": ":", "semikolon": ";", "strichpunkt": ";",
    "bindestrich": "-", "unterstrich": "_", "gleich": "=", "plus": "+",
    "klammer auf": "(", "klammer zu": ")",
}
_NEUE_ZEILE = ("neue zeile", "zeilenumbruch", "absatz", "enter")
_LEER       = ("leerzeichen", "space")
# Steuerkommandos, die AUCH im Diktat greifen (freihändiger Gesamtablauf)
_SENDEN_STAEMME = ("abschick", "absend", "losschick", "abfeuer")
_SENDEN_WORTE   = ("senden", "absenden", "abschicken")
_LOESCH_WORTE   = ("lösche", "löschen", "letztes wort", "weg damit", "korrigieren")
_JA_WORTE          = ("ja", "jawohl", "bestätigen", "bestätige", "okay", "mach")
_NEIN_WORTE        = ("nein", "nee", "abbrechen", "doch nicht", "lass")
# Riskante Aktionen: erst rückfragen (Fehlerkennung darf nichts zerstören)
_RISKANT = {
    "neu_laden":  "neu laden (verwirft ungespeicherte Änderungen)",
    "ausfuehren": "ausführen (ändert das FreeCAD-Dokument)",
}

# dock-Attribut → (Synonyme, Standard-Andockseite)
_PANELS: dict[str, tuple[list[str], object]] = {
    "_dock_cfg":            (["einstellung", "einstellungen", "einst", "konfiguration"], _L),
    "_dock_ki":             (["ki", "assistent", "chat"], _L),
    "_dock_akt":            (["aktion", "aktionen", "akt"], _R),
    "_dock_snip_api":       (["snippet", "snippets", "api", "schnipsel"], _L),
    "_dock_files":          (["datei", "dateien", "dat", "browser", "ordner"], _L),
    "_dock_werkzeugkasten": (["tools", "werkzeugkasten", "bibliothek", "bib"], _R),
    "_dock_werkzeuge":      (["werkzeuge", "werkzeug", "codebaum", "navigation"], _R),
    "_dock_sprache":        (["sprache", "sprachsteuerung"], _R),
    "_dock_fehler":         (["fehler", "sandbox", "fehlermeldung"], _B),
    "_dock_bf_gruppe":      (["hilfe", "zugang", "barrierefrei"], _R),
}


class SprachPanel(QtWidgets.QWidget):
    """Klick-zum-Zuhören-Panel, angebunden an die Aktions-Registry."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self._e         = editor
        self._grammatik = BefehlsGrammatik.aus_registry(editor._aktionen)
        self._worker: SprachWorker | None = None
        self._modell_pfad = finde_vosk_modell()
        self._pending: str | None = None   # wartende Bestätigung (Aktionsname)
        self._baue_ui()
        self._grundstatus()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _baue_ui(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Großer Toggle-Knopf: EIN Klick startet, stoppt von selbst.
        self._btn = QtWidgets.QPushButton("🎤  Zuhören")
        self._btn.setCheckable(True)
        self._btn.setMinimumHeight(64)
        self._btn.setToolTip(
            "Einmal klicken, Befehl sprechen — stoppt automatisch bei der\n"
            "Sprechpause. Nochmal klicken bricht ab. Kein Halten nötig.\n"
            "Beispiele: 'speichern', 'ausführen', 'suche', 'hilfe'")
        self._btn.clicked.connect(self._umschalten)
        lay.addWidget(self._btn)

        # Modus als große, immer sichtbare Knöpfe — barrierefreier als ein
        # Aufklapp-Menü (EIN Klick/Tipp/Blick statt öffnen-dann-wählen).
        self._modus = 0
        modus_zeile = QtWidgets.QHBoxLayout()
        modus_zeile.setSpacing(4)
        self._modus_grp = QtWidgets.QButtonGroup(self)
        self._modus_grp.setExclusive(True)
        self._modus_btns = []
        for i, (txt, tip) in enumerate((
                ("🧭 Befehle", "Panels/Aktionen per Sprache steuern"),
                ("✍ Editor",  "Gesprochenes als Text in den Editor schreiben"),
                ("✍ KI",      "Gesprochenes ins KI-Frage-Feld diktieren"))):
            b = QtWidgets.QPushButton(txt)
            b.setCheckable(True)
            b.setMinimumHeight(38)
            b.setChecked(i == 0)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=i: self._setze_modus(k))
            self._modus_grp.addButton(b, i)
            self._modus_btns.append(b)
            modus_zeile.addWidget(b)
        lay.addLayout(modus_zeile)

        # „Ich höre dich"-Pegel: bewegt sich mit dem Mikrofon-Eingang
        self._pegel = QtWidgets.QProgressBar()
        self._pegel.setRange(0, 100)
        self._pegel.setTextVisible(False)
        self._pegel.setFixedHeight(8)
        self._pegel.setToolTip("Mikrofon-Pegel — bewegt sich, wenn Ton ankommt")
        self._pegel.hide()
        lay.addWidget(self._pegel)

        self._chk_weiter = QtWidgets.QCheckBox("Freihand — nach jedem Befehl weiter zuhören")
        self._chk_weiter.setToolTip(
            "Für freihändiges Arbeiten: hört nach jedem erkannten Befehl\n"
            "automatisch weiter, bis du den Knopf wieder drückst.")
        lay.addWidget(self._chk_weiter)

        self._status = QtWidgets.QLabel("")
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        self._erkannt_lbl = QtWidgets.QLabel("")
        self._erkannt_lbl.setWordWrap(True)
        self._erkannt_lbl.setStyleSheet("color: palette(mid);")
        lay.addWidget(self._erkannt_lbl)

        # Immer verfügbarer Weg (auch ohne Mikro/Modell): Befehl tippen.
        # Ein eigener „▶ Los"-Knopf ist zuverlässiger als die Enter-Taste
        # (die in FreeCADs Dock von globalen Shortcuts geschluckt werden kann)
        # und zugleich barrierefreier.
        zeile = QtWidgets.QHBoxLayout()
        self._eingabe = QtWidgets.QLineEdit()
        self._eingabe.setPlaceholderText("… oder Befehl tippen")
        self._eingabe.returnPressed.connect(self._eingabe_senden)
        zeile.addWidget(self._eingabe, stretch=1)
        self._btn_los = QtWidgets.QPushButton("▶  Los")
        self._btn_los.setMinimumHeight(32)
        self._btn_los.clicked.connect(self._eingabe_senden)
        zeile.addWidget(self._btn_los)
        lay.addLayout(zeile)

        hinweis = QtWidgets.QLabel(
            "Aktionen: " + " · ".join(self._grammatik.alle_beispiele())
            + "\nPanels: »öffne/schließe Dateien, KI, Einstellungen, Fehler …«"
            + "\nDiktat: »diktat editor« / »diktat ki« · »neue zeile« · »punkt«"
            + "\n         »lösche« (korrigieren) · »abschicken« (KI-Frage senden)"
            + "\nAbbrechen: »stop«  ·  zurück: »befehle«")
        hinweis.setWordWrap(True)
        hinweis.setStyleSheet("color: palette(mid); font-size: 11px;")
        lay.addWidget(hinweis)
        lay.addStretch()

    def _eingabe_senden(self):
        self._verarbeite(self._eingabe.text())

    def _grundstatus(self):
        if not HAS_VOSK:
            self._status.setText(
                "🔌 Offline-Erkennung nicht installiert — Tippen funktioniert.\n"
                "   pip install vosk sounddevice")
        elif not self._modell_pfad:
            self._status.setText(
                "📦 Kein deutsches Modell gefunden — Tippen funktioniert.\n"
                "   'vosk-model-small-de-0.15' nach ~/.cache/vosk/ legen")
        else:
            # Modell einmalig im Hintergrund vorladen (großes Modell ~16 s),
            # damit das erste „Zuhören" nicht wartet.
            self._status.setText("🧠 Sprachmodell wird geladen (einmalig) …")
            self._lader = ModellLader(self._modell_pfad, self)
            self._lader.fertig.connect(
                lambda: self._status.setText("Bereit — Knopf klicken und Befehl sprechen."))
            self._lader.start()

    # ── Toggle: starten / abbrechen ──────────────────────────────────────────
    def _umschalten(self):
        if self._btn.isChecked():
            # Statt totem, deaktiviertem Knopf: klarer Hinweis beim Klick.
            if not HAS_VOSK:
                self._btn.setChecked(False)
                self._status.setText("🔌 Bitte erst: pip install vosk sounddevice "
                                     "(oder Befehl unten tippen).")
                return
            if not self._modell_pfad:
                self._btn.setChecked(False)
                self._status.setText("📦 Kein deutsches Vosk-Modell gefunden "
                                     "(oder Befehl unten tippen).")
                return
            if not aufnahme_moeglich():
                self._btn.setChecked(False)
                self._status.setText("🎙 Kein Aufnahme-Tool (parec/pw-record/ffmpeg) "
                                     "gefunden (oder Befehl unten tippen).")
                return
            self._start_zuhoeren()
        else:
            self._stop_zuhoeren()

    def _befehls_wortschatz(self) -> list[str]:
        """Alle Wörter, die im Befehlsmodus vorkommen können — daraus wird
        Vosks Erkennung eingeschränkt (nur diese Wörter → sehr treffsicher)."""
        woerter: set[str] = set()
        for phrasen in self._grammatik._map.values():        # Aktionen
            for p in phrasen:
                woerter.update(p.split())
        for syn, _ in _PANELS.values():                      # Panelnamen
            for s in syn:
                woerter.update(s.split())
        woerter.update([                                     # Verben (volle Wörter)
            "öffne", "öffnen", "öffnet", "zeige", "zeig", "aufmachen", "wechsle",
            "schließe", "schließen", "schliese", "schliesse", "zumachen",
            "verbergen", "ausblenden", "blende", "aus", "den", "die", "das"])
        for grp in (_STOP_WORTE, _UNDO_WORTE, _JA_WORTE, _NEIN_WORTE):
            for w in grp:
                woerter.update(w.split())
        woerter.update(["diktat", "editor", "ki", "befehle", "befehlsmodus",
                        "navigation", "schreib"])            # Modus-Wechsel
        woerter.discard("")
        return sorted(woerter)

    def taste_zuhoeren(self):
        """Vom Tastenkürzel (F4) aufgerufen: Dock zeigen und Zuhören an/aus —
        freihändiger Start ohne Maus."""
        d = getattr(self._e, "_dock_sprache", None)
        if d is not None:
            d.show()
            d.raise_()
        self._btn.setChecked(not self._btn.isChecked())
        self._umschalten()

    def _start_zuhoeren(self):
        if self._worker:
            return
        self._btn.setText("🔴  Höre zu … (klick zum Stoppen)")
        self._status.setText("🎙 Sprich jetzt deinen Befehl …")
        self._pegel.setValue(0)
        self._pegel.show()
        # Befehlsmodus: Vosk auf den bekannten Wortschatz einschränken
        # (treffsicherer). Diktatmodus: freies Modell (grammatik=None).
        grammatik = None
        if self._modus == 0:
            import json
            grammatik = json.dumps(self._befehls_wortschatz() + ["[unk]"])
        self._worker = SprachWorker(self._modell_pfad, grammatik, self)
        self._worker.erkannt.connect(self._nach_erkennung)
        self._worker.fehler.connect(self._on_fehler)
        self._worker.pegel.connect(self._on_pegel)
        self._worker.finished.connect(self._worker_aufraeumen)
        self._worker.start()

    def _on_pegel(self, wert: float):
        self._pegel.setValue(int(wert * 100))

    def _stop_zuhoeren(self):
        if self._worker:
            self._worker.stoppen()
        self._btn.setChecked(False)
        self._btn.setText("🎤  Zuhören")
        self._pegel.hide()
        self._status.setText("Bereit.")

    def _worker_aufraeumen(self):
        self._worker = None

    def _on_fehler(self, msg: str):
        self._stop_zuhoeren()
        self._status.setText(f"❌ Spracherkennung: {msg}")

    def _nach_erkennung(self, text: str):
        # Der Worker ist mit dieser Äußerung fertig.
        self._verarbeite(text)
        if self._chk_weiter.isChecked() and self._btn.isChecked():
            # Freihand: gleich weiter zuhören (Knopf bleibt aktiv)
            self._worker = None
            self._start_zuhoeren()
        else:
            self._stop_zuhoeren()

    # ── Text → Aktion ───────────────────────────────────────────────────────
    def _verarbeite(self, text: str):
        text = (text or "").strip()
        self._eingabe.clear()
        if not text:
            self._status.setText("… nichts gehört. Bitte nochmal.")
            return
        self._erkannt_lbl.setText(f"🗣 »{text}«")
        norm = _normalisieren(text)
        woerter = set(norm.split())

        # Modus per Sprache wechseln (nur kurze Ansagen), dann ggf. diktieren
        if self._modus_per_sprache(norm):
            return
        if self._modus != 0:
            self._diktiere(text, norm)
            return

        # 0) Wartet eine Rückfrage? „ja" bestätigt, „nein" verwirft.
        if self._pending is not None:
            if any(j in woerter for j in _JA_WORTE):
                p = self._pending; self._pending = None
                self._aktion_ausloesen(p)
                return
            if any(n in woerter for n in _NEIN_WORTE):
                self._pending = None
                self._melde("❌ Abgebrochen.")
                return
            self._pending = None   # etwas anderes → Rückfrage verwerfen, weiter

        # 1) rückgängig  2) stop  3) schließen  4) öffnen
        if any(u in woerter for u in _UNDO_WORTE):
            try:
                self._e._editor.undo()
                self._melde("↩ Rückgängig")
            except Exception:
                self._status.setText("↩ Rückgängig nicht möglich")
            return
        if self._stop_kommando(norm):
            return
        if self._panel_schliessen(norm):
            return
        if self._panel_oeffnen(norm):
            return

        # 5) Aktion — riskante erst rückfragen
        name, score = self._grammatik.finde_aktion(text)
        if name and score > 0:
            if name in _RISKANT:
                self._pending = name
                self._melde(f"⚠ {_RISKANT[name]} — sag »ja« zum Bestätigen")
            else:
                self._aktion_ausloesen(name)
        else:
            self._status.setText("🤔 Befehl nicht erkannt — bitte anders formulieren.")
            sprich("Nicht verstanden")

    # ── Diktat ───────────────────────────────────────────────────────────────
    def _setze_modus(self, i: int):
        self._modus = i
        self._pending = None
        b = self._modus_btns[i]
        b.blockSignals(True); b.setChecked(True); b.blockSignals(False)
        if i == 2:   # KI-Frage sichtbar machen
            d = getattr(self._e, "_dock_ki", None)
            if d is not None and hasattr(self._e, "_zeige_panel"):
                self._e._zeige_panel(d, QtCore.Qt.LeftDockWidgetArea)
                d.raise_()
        self._status.setText(
            {0: "🧭 Befehlsmodus", 1: "✍ Diktat → Editor",
             2: "✍ Diktat → KI-Frage"}.get(i, ""))

    def _modus_per_sprache(self, norm: str) -> bool:
        """Kurze Ansagen wechseln den Modus (verhindert versehentliches
        Umschalten mitten im Diktat: nur bei ≤ 3 Wörtern)."""
        w = norm.split()
        if len(w) > 3:
            return False
        will_diktat = ("diktat" in w or "diktier" in norm or "schreib" in norm)
        if will_diktat and "editor" in norm:
            self._setze_modus(1); return True
        if will_diktat and ("ki" in w or "frage" in norm):
            self._setze_modus(2); return True
        if any(x in w for x in ("befehl", "befehle", "befehlsmodus", "navigation")):
            self._setze_modus(0); return True
        return False

    def _ziel_widget(self):
        if self._modus == 1:
            return getattr(self._e, "_editor", None)
        if self._modus == 2:
            return getattr(self._e, "_frage_feld", None)
        return None

    def _diktat_text(self, text: str, norm: str) -> str:
        if norm in _NEUE_ZEILE:
            return "\n"
        if norm in _LEER:
            return " "
        if norm in _SATZZEICHEN:
            return _SATZZEICHEN[norm]
        return text.strip() + " "

    def _diktiere(self, text: str, norm: str):
        w = norm.split()
        # „stop" beendet das Zuhören auch im Diktat
        if any(x in w for x in _STOP_WORTE):
            self._stop_zuhoeren(); return
        # Kurze Steuerkommandos greifen auch mitten im Diktat (≤ 3 Wörter)
        if len(w) <= 3:
            if norm in _LOESCH_WORTE or norm.startswith("lösch"):
                self._letztes_wort_loeschen(); return
            ist_senden = (norm in _SENDEN_WORTE
                          or any(norm.startswith(s) for s in _SENDEN_STAEMME))
            if ist_senden and self._modus == 2:
                self._ki_frage_senden(); return
        ziel = self._ziel_widget()
        if ziel is None:
            self._status.setText("⚠ Kein Ziel für Diktat gefunden")
            return
        einfuege = self._diktat_text(text, norm)
        c = ziel.textCursor()
        c.insertText(einfuege)
        ziel.setTextCursor(c)
        try:
            ziel.setFocus()
        except Exception:
            pass
        gezeigt = einfuege.replace("\n", "⏎")
        self._status.setText(f"✍ eingefügt: »{gezeigt}«")

    def _letztes_wort_loeschen(self):
        """Korrektur per Stimme: letztes Wort im Diktat-Ziel entfernen."""
        ziel = self._ziel_widget()
        if ziel is None:
            return
        t = ziel.toPlainText().rstrip()
        cut = max(t.rfind(" "), t.rfind("\n"))
        neu = (t[:cut] + " ") if cut >= 0 else ""
        ziel.setPlainText(neu)
        c = ziel.textCursor()
        c.movePosition(c.MoveOperation.End if hasattr(c, "MoveOperation") else c.End)
        ziel.setTextCursor(c)
        self._status.setText("🧽 letztes Wort gelöscht")

    def _ki_frage_senden(self):
        """Diktierte KI-Frage direkt abschicken — ohne Moduswechsel/Maus."""
        feld = getattr(self._e, "_frage_feld", None)
        if feld is None or not feld.toPlainText().strip():
            self._status.setText("⚠ KI-Frage ist noch leer")
            return
        try:
            self._e._aktionen.aktion("ki_fragen").trigger()
            self._melde("📤 Frage an die KI geschickt")
        except Exception as e:
            self._status.setText(f"❌ Senden fehlgeschlagen: {e}")

    def _aktion_ausloesen(self, name: str):
        try:
            akt = self._e._aktionen.aktion(name)
            akt.trigger()
            rueck = f"▶ {akt.text().strip()}"
            self._status.setText(f"✅ {rueck}")
            self._e._set_status(f"🎤 {rueck}")
            sprich("Okay")
        except Exception as e:
            self._status.setText(f"❌ Aktion »{name}« fehlgeschlagen: {e}")

    def _melde(self, text: str):
        self._status.setText(text)
        try:
            self._e._set_status(f"🎤 {text}")
        except Exception:
            pass
        sprich("Okay")

    def _finde_panel(self, t: str):
        """Bestes Dock zum Text (ohne Verb-Prüfung). (dock, area) oder (None, None)."""
        woerter = set(t.split())
        best, best_score, best_area = None, 0, None
        for attr, (syn, area) in _PANELS.items():
            score = sum(1 for s in syn if (s in t if " " in s else s in woerter))
            if score > best_score:
                best, best_score, best_area = attr, score, area
        if not best:
            return None, None
        return getattr(self._e, best, None), best_area

    def _stop_kommando(self, t: str) -> bool:
        """„stop / abbrechen / halt" → laufende Aktion abbrechen bzw. Freihand
        beenden. True, wenn es als Stop-Befehl erkannt wurde."""
        if not any(w in t.split() for w in _STOP_WORTE):
            return False
        e = self._e
        vs = getattr(e, "_vorschau", None)
        if vs is not None and getattr(vs, "exec_laeuft", lambda: False)():
            vs.abbruch_anfordern()
            self._melde("⏹ Ausführung abgebrochen")
        elif getattr(e, "_ki_aktiv", False) and hasattr(e, "_ki_stoppen"):
            e._ki_stoppen()
            self._melde("⏹ KI-Anfrage gestoppt")
        elif self._btn.isChecked():
            self._stop_zuhoeren()
            self._melde("⏹ Zuhören beendet")
        else:
            self._melde("⏹ Es läuft gerade nichts.")
        return True

    def _panel_oeffnen(self, t: str) -> bool:
        """„öffne/zeig <panel>" → passendes Dock einblenden."""
        if not any(w.startswith(s) for w in t.split() for s in _OEFFNEN_STAEMME):
            return False
        dock, area = self._finde_panel(t)
        if dock is None or not hasattr(self._e, "_zeige_panel"):
            return False
        self._e._zeige_panel(dock, area)
        dock.raise_()
        self._melde(f"✅ {dock.windowTitle().strip()} geöffnet")
        return True

    def _panel_schliessen(self, t: str) -> bool:
        """„schließe/verbirg <panel>" → passendes Dock ausblenden."""
        if not any(w.startswith(s) for w in t.split() for s in _SCHLIESSEN_STAEMME):
            return False
        dock, _ = self._finde_panel(t)
        if dock is None:
            return False
        dock.hide()
        self._melde(f"✅ {dock.windowTitle().strip()} geschlossen")
        return True

    # ── sauber schließen ────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._worker:
            self._worker.stoppen()
            self._worker.wait(1000)
        super().closeEvent(event)
