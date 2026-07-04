# -*- coding: utf-8 -*-
"""
vorschau_controller.py
──────────────────────
Vorschau – Interaktiver FreeCAD-3D-Viewport direkt im Editor-Tab.

Strategie: Widget-Embedding via setParent()
  FreeCAD läuft im selben Prozess. Der aktive View3DInventor (QWidget) wird
  temporär per setParent() in den Vorschau-Tab eingebettet.
  Der User kann das 3D-Modell drehen, zoomen und schwenken — genau wie im
  normalen FreeCAD-Viewport. Beim Schließen des Tabs wird der View wieder
  in sein ursprüngliches MdiSubWindow zurückgesetzt.

Ablauf:
  1. ▶ Ausführen  → exec() im FreeCAD-Namespace, recompute(), fitAll()
  2. View3DInventor-Widget per setParent() in Tab-Container einbetten
  3. Volle Maus-Interaktion: drehen / zoomen / schwenken
  4. 🔄 Aktualisieren → Code erneut ausführen, Widget bleibt eingebettet
  5. ✕ Schließen → Widget per setParent() zurück ins MdiSubWindow

Öffentliche API:
  vorschau_starten()    – Sidebar-Button "👁 Vorschau"
  vorschau_schliessen() – Tab-✕ oder Schließen-Button
  _vorschau_init()      – am Ende von MakroEditor.__init__()
"""

import ast
import io as _io
import contextlib as _cl
import traceback as _tb

from core.qt_compat import QtWidgets, QtCore, QtGui
from core import theme
from core import schrift


class Vorschau:
    """
    Interaktiver FreeCAD-3D-Viewport eingebettet in den Editor-Tab.

    Greift über self._e auf den Host zurück für:
      _editor_tab_widget, _editor   (aktiver Editor-Tab)
      _set_status()
      fehler_anzeigen()             (vom KI-Controller bereitgestellt)
      findChildren()                (Qt-Methode des Hauptfensters)
    """

    def __init__(self, editor):
        self._e = editor

    # ── Init ──────────────────────────────────────────────────────────────
    def _vorschau_init(self):
        self._vorschau_tab_index:    int                      = -1
        self._vorschau_widget:       QtWidgets.QWidget | None = None
        self._vorschau_container:    QtWidgets.QWidget | None = None
        self._vorschau_status_lbl:   QtWidgets.QLabel  | None = None
        self._vorschau_log_box:      QtWidgets.QPlainTextEdit | None = None
        self._vorschau_view_widget:  QtWidgets.QWidget | None = None  # der eingebettete View
        self._vorschau_orig_parent:  QtWidgets.QWidget | None = None  # MdiSubWindow
        self._vorschau_orig_geom:    QtCore.QRect      | None = None
        self._vorschau_shot_timer:   QtCore.QTimer     | None = None
        self._vorschau_code_override:  str | None = None
        self._vorschau_letzter_fehler: str | None = None
        self._vorschau_letzter_code:   str | None = None
        self._letzter_exec_ausgabe:    str        = ""
        self._exec_laeuft:             bool       = False
        self._exec_abbruch:            bool       = False

        self._e._editor_tab_widget.tabCloseRequested.connect(
            self._vorschau_tab_close_requested)

    # ── Öffentlich ────────────────────────────────────────────────────────
    def vorschau_starten(self, code: str = None):
        """Öffnet den Vorschau-Tab. Wenn code angegeben, wird er sofort ausgeführt."""
        if self._vorschau_tab_index >= 0:
            self._e._editor_tab_widget.setCurrentIndex(self._vorschau_tab_index)
        else:
            self._vorschau_widget = self._baue_vorschau_tab()
            idx = self._e._editor_tab_widget.addTab(self._vorschau_widget, "👁 Vorschau")
            self._vorschau_tab_index = idx
            self._e._editor_tab_widget.setCurrentIndex(idx)

        if code:
            self._vorschau_code_override = code
            self._e._set_status("👁 Vorschau-Tab — führe KI-Code aus …")
            self._vorschau_ausfuehren()
        else:
            self._e._set_status("👁 Vorschau-Tab geöffnet — ▶ Ausführen drücken")

    def vorschau_schliessen(self):
        self._view_zurueckgeben()
        if self._vorschau_shot_timer:
            self._vorschau_shot_timer.stop()
            self._vorschau_shot_timer = None
        if self._vorschau_widget is not None:
            idx = self._e._editor_tab_widget.indexOf(self._vorschau_widget)
            if idx >= 0:
                self._e._editor_tab_widget.removeTab(idx)
        self._vorschau_tab_index  = -1
        self._vorschau_widget     = None
        self._vorschau_container  = None
        self._vorschau_status_lbl = None
        self._vorschau_log_box    = None
        self._e._set_status("👁 Vorschau geschlossen")

    # ── Abbruch laufender Ausführung ──────────────────────────────────────
    def exec_laeuft(self) -> bool:
        return getattr(self, "_exec_laeuft", False)

    def abbruch_anfordern(self):
        """⏹-Button bzw. F5/F9 während eines Laufs — der Wächter in
        _vorschau_exec stoppt an der nächsten Python-Zeile."""
        if self.exec_laeuft():
            self._exec_abbruch = True
            self._e._set_status(
                "⏹ Abbruch angefordert — stoppt an der nächsten Python-Zeile",
                ms=0)

    def _lauf_ui_setzen(self, laeuft: bool) -> None:
        """Schaltet den ▶-Button im Vorschau-Tab in den Stopp-Modus und
        zurück (ein Button, zwei Zustände — kein zusätzliches Element)."""
        btn = getattr(self, "_btn_vp_aus", None)
        if btn is not None:
            if laeuft:
                btn.setText("⏹  Stopp")
                btn.setToolTip(
                    "Laufende Ausführung abbrechen — stoppt an der nächsten\n"
                    "Python-Zeile (eine laufende FreeCAD-Operation selbst\n"
                    "ist nicht unterbrechbar)")
            else:
                btn.setText("▶  Ausführen")
                btn.setToolTip("Code ausführen und 3D-Viewport einbetten")
        for name in ("_btn_vp_akt", "_btn_vp_fit"):
            b = getattr(self, name, None)
            if b is not None:
                b.setEnabled(not laeuft)

    # ── Auswahl ausführen (F9) ────────────────────────────────────────────
    def auswahl_ausfuehren(self):
        """F9 — führt nur die markierten Zeilen (oder die aktuelle Zeile)
        in FreeCAD aus. Die Selektion wird auf ganze Zeilen erweitert und
        der Code mit Leerzeilen auf seine Originalposition aufgefüllt,
        damit Fehler-Zeilennummern weiter auf die Editor-Zeilen zeigen."""
        e = self._e
        if self.exec_laeuft():
            self.abbruch_anfordern()
            return
        cursor = e._editor.textCursor()
        doc    = e._editor.document()
        if cursor.hasSelection():
            block = doc.findBlock(cursor.selectionStart())
            ende  = doc.findBlock(cursor.selectionEnd())
            # Endet die Selektion genau am Zeilenanfang, zählt die Zeile nicht mit
            if (ende.blockNumber() > block.blockNumber()
                    and cursor.selectionEnd() == ende.position()):
                ende = ende.previous()
        else:
            block = ende = cursor.block()
        start_zeile = block.blockNumber()
        zeilen = []
        b = block
        while b.isValid():
            zeilen.append(b.text())
            if b.blockNumber() >= ende.blockNumber():
                break
            b = b.next()
        text = "\n".join(zeilen)
        if not text.strip():
            e._set_status("⚠ Keine ausführbaren Zeilen markiert (F9)")
            return
        import textwrap
        code = "\n" * start_zeile + textwrap.dedent(text)
        n = len(zeilen)
        if (self.ausfuehren_ohne_vorschau(code, transaktion="Auswahl (F9)")
                and not self._letzter_exec_ausgabe.strip()):
            e._set_status(f"✅ Auswahl ausgeführt ({n} Zeile{'' if n == 1 else 'n'}) "
                          "— Ergebnis im FreeCAD-Fenster")

    # ── Stilles Ausführen (F5 / F9 — ohne Vorschau-Tab) ───────────────────
    def ausfuehren_ohne_vorschau(self, code: str = None,
                                 transaktion: str = "Makro (F5)") -> bool:
        """Führt Code in FreeCAD aus, ohne Vorschau-Tab oder Viewport-
        Einbettung — das Ergebnis zeigt das FreeCAD-Hauptfenster.
        Nur bei Fehlern öffnet sich das Fehler-Panel. True bei Erfolg."""
        e = self._e
        if self.exec_laeuft():
            e._set_status("⏳ Es läuft bereits eine Ausführung — F5 bricht sie ab")
            return False
        if code is None:
            code = e._editor.toPlainText().strip()
        if not code:
            e._set_status("⚠ Editor ist leer")
            return False

        try:
            ast.parse(code)
        except SyntaxError as ex:
            if hasattr(e._editor, "setze_fehler_zeilen") and ex.lineno:
                e._editor.setze_fehler_zeilen([ex.lineno - 1])
            self._stiller_fehler(f"SyntaxError Zeile {ex.lineno}: {ex.msg}", code)
            return False
        if hasattr(e._editor, "setze_fehler_zeilen"):
            e._editor.setze_fehler_zeilen([])

        # Auto-Backup wie bei der KI-Vorschau
        try:
            import FreeCAD as _App
            _doc = _App.ActiveDocument
            if _doc and _doc.FileName:
                import shutil as _sh
                _sh.copy2(_doc.FileName, _doc.FileName + ".vorschau-backup")
        except Exception:
            pass

        e._set_status("⏳ Führe aus … (F5 = Abbrechen)", ms=0)
        fehler = self._vorschau_exec(code, transaktion=transaktion)
        if fehler:
            if fehler.startswith("⏹"):
                # Absichtlicher Abbruch ist kein Fehler — Dock bleibt zu
                e._set_status(fehler, ms=0)
                return False
            import re as _re
            _m = _re.search(r"Zeile (\d+)", fehler)
            if _m and hasattr(e._editor, "setze_fehler_zeilen"):
                e._editor.setze_fehler_zeilen([int(_m.group(1)) - 1])
            self._stiller_fehler(fehler, code)
            return False

        ausgabe = getattr(self, "_letzter_exec_ausgabe", "").strip()
        if ausgabe:
            # print()-Ausgabe still ins Fehler-Panel parken (Dock bleibt zu)
            panel = getattr(e, "_fehler_inhalt", None)
            if panel is not None:
                panel.ausgabe_starten(code)
                panel.ausgabe_anhaengen(ausgabe)
                panel._sb_status.setText("✅ Erfolgreich ausgeführt")
                panel._sb_rahmen("ok")
            e._set_status("✅ Ausgeführt — Ausgabe liegt im ⚠ Fehler-Panel")
        else:
            e._set_status("✅ Ausgeführt — Ergebnis im FreeCAD-Fenster")
        return True

    def _stiller_fehler(self, fehler: str, code: str) -> None:
        """Fehler aus dem stillen Lauf: Panel befüllen und Dock öffnen."""
        self._vorschau_letzter_fehler = fehler
        self._vorschau_letzter_code   = code
        self._vorschau_fehler_panel_befuellen(fehler)
        if hasattr(self._e, "_dock_fehler"):
            self._e._dock_fehler.show()
            self._e._dock_fehler.raise_()
        self._e._set_status(f"❌ {fehler}", ms=0)

    # ── Tab-UI ────────────────────────────────────────────────────────────
    def _baue_vorschau_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(w)
        root.setContentsMargins(theme.ABST_L, theme.ABST_M, theme.ABST_L, theme.ABST_M)
        root.setSpacing(theme.ABST_M)

        # Titelzeile
        tz = QtWidgets.QHBoxLayout()
        tl = QtWidgets.QLabel("👁  Live-Vorschau  —  FreeCAD 3D-Viewport  (drehbar)")
        tl.setStyleSheet(theme.STY_VORSCHAU_TITEL(schrift.pt(schrift.STUFE_LG)))
        tz.addWidget(tl)
        tz.addStretch()
        bx = QtWidgets.QPushButton("✕  Schließen")
        bx.setFixedHeight(theme.VORSCHAU_CLOSE_BTN_H)
        bx.setStyleSheet(theme.STY_VORSCHAU_CLOSE_BTN(schrift.pt(schrift.STUFE_BASE)))
        bx.clicked.connect(self.vorschau_schliessen)
        tz.addWidget(bx)
        root.addLayout(tz)

        # Status
        self._vorschau_status_lbl = QtWidgets.QLabel(
            "Bereit — '▶ Ausführen' drücken")
        self._vorschau_status_lbl.setStyleSheet(
            theme.STY_VORSCHAU_STATUS(schrift.pt(schrift.STUFE_BASE)))
        root.addWidget(self._vorschau_status_lbl)

        # Container für den eingebetteten View
        self._vorschau_container = QtWidgets.QWidget()
        self._vorschau_container.setObjectName("VorschauContainer")
        self._vorschau_container.setMinimumHeight(theme.VORSCHAU_CONTAINER_MIN_H)
        self._vorschau_container.setStyleSheet(theme.STY_VORSCHAU_CONTAINER)
        container_lay = QtWidgets.QVBoxLayout(self._vorschau_container)
        container_lay.setContentsMargins(theme.ABST_KEIN, theme.ABST_KEIN, theme.ABST_KEIN, theme.ABST_KEIN)

        # Platzhalter-Label (wird ersetzt sobald der View eingebettet ist)
        self._vorschau_placeholder = QtWidgets.QLabel(
            f"<span style='font-size:{schrift.pt(schrift.STUFE_ICON)}pt;'>👁</span><br>"
            f"<span style='font-size:{schrift.pt(schrift.STUFE_LG)}pt;'>"
            "FreeCAD-Viewport erscheint hier<br>"
            "nach ▶ Ausführen</span>")
        self._vorschau_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self._vorschau_placeholder.setStyleSheet(theme.STY_VORSCHAU_PLACEHOLDER)
        container_lay.addWidget(self._vorschau_placeholder)
        root.addWidget(self._vorschau_container, stretch=1)

        # Buttons
        bz = QtWidgets.QHBoxLayout()
        bz.setSpacing(theme.ABST_L)

        def _btn(label, slot, tip=""):
            b = QtWidgets.QPushButton(label)
            b.setMinimumHeight(theme.VORSCHAU_BTN_H)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bz.addWidget(b)
            return b

        self._btn_vp_aus  = _btn("▶  Ausführen",
                                  self._vorschau_ausfuehren_oder_stopp,
                                  "Code ausführen und 3D-Viewport einbetten")
        self._btn_vp_akt  = _btn("🔄  Aktualisieren",
                                  self._vorschau_ausfuehren,
                                  "Code erneut ausführen — das vorherige Vorschau-\n"
                                  "Ergebnis wird ersetzt (keine doppelten Körper)")
        self._btn_vp_fit  = _btn("⊡  Einpassen",
                                  self._vorschau_fit_all,
                                  "fitAll() — Modell ins Bild einpassen")
        self._btn_vp_fehler = None
        self._btn_vp_ki_fix = None
        root.addLayout(bz)

        warn = QtWidgets.QLabel(
            "⚠  Code wird direkt in FreeCAD ausgeführt — Änderungen am Dokument sind real.")
        warn.setStyleSheet(theme.STY_VORSCHAU_WARN(schrift.pt(schrift.STUFE_SM)))
        warn.setWordWrap(True)
        root.addWidget(warn)

        return w

    # ── Ausführen ────────────────────────────────────────────────────────
    def _vorschau_ausfuehren_oder_stopp(self):
        """▶-Button im Vorschau-Tab: startet einen Lauf — oder bricht den
        laufenden ab (der Button zeigt dann ⏹ Stopp)."""
        if self.exec_laeuft():
            self.abbruch_anfordern()
        else:
            self._vorschau_ausfuehren()

    def _vorschau_ausfuehren(self):
        if self.exec_laeuft():
            return
        # Priorität: override (KI-Code) → Editor
        code = getattr(self, "_vorschau_code_override", None) or self._e._editor.toPlainText().strip()
        self._vorschau_code_override = None
        if not code:
            self._vorschau_log("⚠  Editor ist leer.")
            return

        panel = getattr(self._e, "_fehler_inhalt", None)

        try:
            ast.parse(code)
        except SyntaxError as e:
            self._vorschau_status(f"❌ SyntaxError Zeile {e.lineno}")
            if hasattr(self._e._editor, "setze_fehler_zeilen") and e.lineno:
                self._e._editor.setze_fehler_zeilen([e.lineno - 1])
            if panel is not None:
                panel._sandbox_ergebnis(False, f"❌ SyntaxError Zeile {e.lineno}: {e.msg}", code)
                if hasattr(self._e, "_dock_fehler"):
                    self._e._dock_fehler.show()
                    self._e._dock_fehler.raise_()
            return

        if hasattr(self._e._editor, "setze_fehler_zeilen"):
            self._e._editor.setze_fehler_zeilen([])

        # Sandbox als einzige Ausgabe starten
        if panel is not None:
            panel.ausgabe_starten(code)
            if hasattr(self._e, "_dock_fehler"):
                self._e._dock_fehler.show()
                self._e._dock_fehler.raise_()
            panel.ausgabe_anhaengen("✅ Syntax korrekt")
        self._vorschau_status("⏳ Code wird ausgeführt …")

        # Vorherige Vorschau-Läufe zurücknehmen — sonst erzeugt jedes
        # 🔄 Aktualisieren neue Körper statt das Ergebnis zu ersetzen
        self._vorherige_vorschau_zuruecknehmen(panel)

        # Auto-Backup
        try:
            import FreeCAD as _App
            _doc = _App.ActiveDocument
            if _doc and _doc.FileName:
                import shutil as _sh
                backup = _doc.FileName + ".vorschau-backup"
                _sh.copy2(_doc.FileName, backup)
                if panel is not None:
                    panel.ausgabe_anhaengen(f"💾 Backup: {backup}")
        except Exception:
            pass

        if panel is not None:
            panel.ausgabe_anhaengen("▶ Führe Code aus …")

        fehler = self._vorschau_exec(code)
        if fehler and fehler.startswith("⏹"):
            # Absichtlicher Abbruch ist kein Fehler
            self._vorschau_status(fehler)
            if panel is not None:
                panel.ausgabe_anhaengen(fehler)
                panel._sb_status.setText("⏹ Abgebrochen")
            self._e._set_status(fehler, ms=0)
            return
        if fehler:
            self._vorschau_status(f"❌ {fehler}")
            self._vorschau_letzter_fehler = fehler
            self._vorschau_letzter_code   = code
            import re as _re
            _m = _re.search(r"Zeile (\d+)", fehler)
            if _m and hasattr(self._e._editor, "setze_fehler_zeilen"):
                self._e._editor.setze_fehler_zeilen([int(_m.group(1)) - 1])
            self._vorschau_fehler_panel_befuellen(fehler)
            if hasattr(self._e, "_dock_fehler"):
                self._e._dock_fehler.show()
                self._e._dock_fehler.raise_()
            if hasattr(self._e, "_btn_ersetzen"):
                self._e._btn_ersetzen.setEnabled(False)
            if hasattr(self._e, "_btn_einfuegen"):
                self._e._btn_einfuegen.setEnabled(False)
            return

        self._vorschau_letzter_fehler = None
        self._vorschau_letzter_code   = None

        if panel is not None:
            exec_ausgabe = getattr(self, "_letzter_exec_ausgabe", "")
            if exec_ausgabe.strip():
                panel.ausgabe_anhaengen(exec_ausgabe.strip())
            panel.ausgabe_anhaengen("✅ Ausgeführt — bette Viewport ein …")

        self._vorschau_status("✅ Ausgeführt …")

        # View einbetten nach kurzem Delay (FreeCAD braucht einen Frame)
        self._vorschau_shot_timer = QtCore.QTimer(self._e)
        self._vorschau_shot_timer.setSingleShot(True)
        self._vorschau_shot_timer.timeout.connect(self._view_einbetten)
        self._vorschau_shot_timer.start(200)

    def _vorherige_vorschau_zuruecknehmen(self, panel=None) -> None:
        """Nimmt alle direkt aufeinanderfolgenden „KI-Vorschau"-Transactions
        per Undo zurück, damit ein neuer Lauf das Ergebnis ERSETZT statt
        Duplikate zu erzeugen. Fremde Transactions (manuelle Änderungen,
        F5-Läufe) haben andere Namen und bleiben unangetastet."""
        try:
            import FreeCAD as App
            doc = App.ActiveDocument
            if doc is None:
                return
            zurueck = 0
            while (getattr(doc, "UndoNames", None)
                   and doc.UndoNames[0] == "KI-Vorschau"
                   and zurueck < 20):          # Sicherheitsgrenze
                doc.undo()
                zurueck += 1
            if zurueck:
                doc.recompute()
                if panel is not None:
                    panel.ausgabe_anhaengen(
                        f"↩ Vorheriges Vorschau-Ergebnis ersetzt "
                        f"({zurueck} Lauf{'' if zurueck == 1 else 'e'} zurückgenommen)")
        except Exception:
            pass

    def _vorschau_exec(self, code: str, nur_pruefen: bool = False,
                       transaktion: str = "KI-Vorschau"):
        """exec() im echten FreeCAD-Namespace. Gibt None oder Fehlermeldung zurück.

        nur_pruefen=True: Transaction wird auch bei Erfolg abgebrochen — keine
        dauerhaften FreeCAD-Änderungen. Zum Laufzeit-Check vor dem Einfügen in den Editor.
        transaktion: Name der Undo-Transaction — die Vorschau nimmt vor einem
        neuen Lauf nur ihre eigenen „KI-Vorschau"-Transactions zurück.
        """
        if self.exec_laeuft():
            return "⏳ Es läuft bereits eine Ausführung — ⏹/F5 bricht sie ab"
        try:
            import FreeCAD as App
            import FreeCADGui as Gui
        except ImportError:
            return "FreeCAD nicht verfügbar"

        ns = {
            "__builtins__": __builtins__,
            "__name__":     "__vorschau__",
            "App": App, "Gui": Gui,
        }
        import importlib
        for mod in ("Part", "PartDesign", "Sketcher", "Draft", "Mesh"):
            try:
                ns[mod] = importlib.import_module(mod)
            except ImportError:
                pass
        # Part-Workbench explizit initialisieren damit Part::Cut/.Base/.Tool existieren
        try:
            import Part as _Part
            _Part.show  # triggert Workbench-Initialisierung
        except Exception:
            pass

        import re as _re
        code = _re.sub(r'\bPySide2\b', 'PySide6', code)

        # Bekannte halluzinierte FreeCAD-Typen vor exec() erkennen
        _FAKE_TYPEN = {
            "Part::UnionForTwoVolumes", "Part::Union", "Part::BooleanUnion",
            "Part::BooleanCut", "Part::Subtract", "Part::Difference",
            "Part::Merge", "Part::Intersection", "Part::BooleanIntersection",
            "Part::Profile2D", "Part::Extrude2D", "Part::Shell2D",
            "Part::Loft2D", "Part::Solid2D",
        }
        for fake in _FAKE_TYPEN:
            if fake in code:
                return (
                    f"❌ Unbekannter FreeCAD-Typ: '{fake}'\n"
                    f"   Dieser Typ existiert nicht in FreeCAD.\n"
                    f"   KI-Code wurde NICHT ausgeführt.\n"
                    f"   → Bitte KI erneut anfragen oder Beschreibung anpassen."
                )

        # Halluzination: .Base auf Part-Primitive (Box, Sphere, Cylinder …)
        # PrimitivePy-Objekte haben kein .Base-Attribut
        _PRIMITIVE_TYPEN = (
            "Part::Box", "Part::Sphere", "Part::Cylinder",
            "Part::Cone", "Part::Torus", "Part::Wedge",
            "Part::Ellipsoid", "Part::Prism", "Part::RegularPolygon",
        )
        _base_fehler = _re.search(r'\.Base\s*=', code)
        if _base_fehler:
            # Prüfen ob eine Variable die auf ein Primitiv zeigt .Base zugewiesen bekommt
            _prim_vars = set()
            for _pt in _PRIMITIVE_TYPEN:
                for _m in _re.finditer(
                        r'(\w+)\s*=\s*\w+\.addObject\s*\(\s*["\']' + _re.escape(_pt) + r'["\']',
                        code):
                    _prim_vars.add(_m.group(1))
            for _var in _prim_vars:
                if _re.search(r'\b' + _re.escape(_var) + r'\s*\.\s*Base\s*=', code):
                    return (
                        f"❌ Halluziniertes Attribut '.Base' auf Part-Primitiv '{_var}'\n"
                        f"   Part::Box / Sphere / Cylinder usw. haben KEIN .Base-Attribut.\n"
                        f"   KI-Code wurde NICHT ausgeführt.\n"
                        f"   Tipp: Für Boolean-Operationen → Part.fuse() / Part.cut() verwenden,\n"
                        f"   oder Part::Cut / Part::Fuse als doc.addObject() mit .Base und .Tool\n"
                        f"   nur auf dem Boolean-Objekt selbst setzen (nicht auf den Primitiven)."
                    )

        doc = App.ActiveDocument
        in_transaction = False
        _stdout_buf = _io.StringIO()

        # Abbruch-Wächter: exec() läuft im GUI-Thread und friert das Fenster
        # ein. Der Trace-Hook pumpt deshalb alle ~0,1 s die Qt-Events, damit
        # ⏹/F5 klickbar bleiben, und wirft bei angefordertem Abbruch einen
        # KeyboardInterrupt (stoppt nur zwischen Python-Zeilen — eine
        # laufende FreeCAD-C++-Operation ist nicht unterbrechbar).
        import sys as _sys
        import time as _time
        self._exec_laeuft  = True
        self._exec_abbruch = False
        self._lauf_ui_setzen(True)
        _pump = {"zaehler": 0, "letzter": _time.monotonic()}

        def _trace_zeile(frame, event, arg):
            if event == "line":
                _pump["zaehler"] += 1
                if _pump["zaehler"] >= 200:
                    _pump["zaehler"] = 0
                    jetzt = _time.monotonic()
                    if jetzt - _pump["letzter"] >= 0.1:
                        _pump["letzter"] = jetzt
                        QtWidgets.QApplication.processEvents()
                        if self._exec_abbruch:
                            raise KeyboardInterrupt("Vom Benutzer abgebrochen")
            return _trace_zeile

        def _trace_start(frame, event, arg):
            if frame.f_code.co_filename != "<vorschau>":
                return None
            return _trace_zeile

        try:
            if doc:
                doc.openTransaction("KI-Prüflauf" if nur_pruefen else transaktion)
                in_transaction = True
            _sys.settrace(_trace_start)
            with _cl.redirect_stdout(_stdout_buf):
                exec(compile(code, "<vorschau>", "exec"), ns)  # noqa: S102
        except KeyboardInterrupt:
            if in_transaction:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            try:
                if App.ActiveDocument:
                    App.ActiveDocument.recompute()
            except Exception:
                pass
            self._letzter_exec_ausgabe = _stdout_buf.getvalue()
            return "⏹ Abgebrochen — FreeCAD-Änderungen wurden zurückgenommen"
        except Exception as e:
            if in_transaction:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            zeilen = _tb.format_exc().strip().splitlines()
            ausgabe = _stdout_buf.getvalue()
            log_text = (ausgabe + "\n" if ausgabe else "") + "\n".join(zeilen[-8:])
            self._vorschau_log(log_text.strip())
            self._letzter_exec_ausgabe = ""
            # Zeilennummer aus dem Traceback holen (letzter Frame im User-Code)
            zeile = None
            tb = e.__traceback__
            while tb is not None:
                if tb.tb_frame.f_code.co_filename == "<vorschau>":
                    zeile = tb.tb_lineno
                tb = tb.tb_next
            if zeile:
                return f"{type(e).__name__} in Zeile {zeile}: {e}"
            return f"{type(e).__name__}: {e}"
        finally:
            _sys.settrace(None)
            self._exec_laeuft = False
            self._lauf_ui_setzen(False)

        self._letzter_exec_ausgabe = _stdout_buf.getvalue()

        if nur_pruefen:
            # Nur Laufzeit-Check: alle FreeCAD-Änderungen rückgängig machen
            if in_transaction:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            return None

        # recompute + fitAll
        try:
            if App.ActiveDocument:
                App.ActiveDocument.recompute()
        except Exception:
            pass

        if in_transaction:
            try:
                doc.commitTransaction()
            except Exception:
                pass

        try:
            v = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument else None
            if v:
                v.fitAll()
        except Exception:
            pass

        return None

    # ── View einbetten / zurückgeben ──────────────────────────────────────
    def _view_einbetten(self):
        """Holt den aktiven View3DInventor und bettet ihn in den Container ein."""
        try:
            import FreeCADGui as Gui
        except ImportError:
            self._vorschau_log("❌ FreeCAD nicht verfügbar")
            return

        # Alten View ggf. zurückgeben bevor neuer geholt wird
        if self._vorschau_view_widget:
            self._view_zurueckgeben()

        # View-Widget aus FreeCAD holen
        view_widget = self._hole_view_widget(Gui)
        if view_widget is None:
            self._vorschau_log(
                "⚠  Kein aktiver 3D-View gefunden.\n"
                "   Öffne ein FreeCAD-Dokument und führe den Code erneut aus.")
            self._vorschau_status("⚠ Kein 3D-View gefunden")
            return

        # Original-Parent und Geometrie merken (für Rückgabe)
        self._vorschau_orig_parent = view_widget.parent()
        self._vorschau_orig_geom   = view_widget.geometry()

        # Dock-Zustände sichern — setParent() löst Qt-Relayout aus der Docks versteckt
        self._vorschau_dock_zustaende = [
            (d, d.isVisible())
            for d in self._e.findChildren(QtWidgets.QDockWidget)
        ]

        # Platzhalter ausblenden
        self._vorschau_placeholder.hide()

        # UI einfrieren während setParent() das Fenster kurz versteckt —
        # verhindert das sichtbare Schließen/Öffnen des Hauptfensters.
        main_win = self._e.window()
        main_win.setUpdatesEnabled(False)
        try:
            lay = self._vorschau_container.layout()
            self._vorschau_view_widget = view_widget
            view_widget.setParent(self._vorschau_container)
            lay.addWidget(view_widget)
            view_widget.show()
        finally:
            main_win.setUpdatesEnabled(True)
            main_win.repaint()

        # Docks wiederherstellen die Qt beim setParent() versteckt hat
        for dock, war_sichtbar in self._vorschau_dock_zustaende:
            if war_sichtbar and not dock.isVisible():
                dock.show()

        self._vorschau_status("✅ 3D-Viewport eingebettet — drehen/zoomen mit Maus")
        panel = getattr(self._e, "_fehler_inhalt", None)
        if panel is not None:
            panel.ausgabe_anhaengen("📐 Viewport eingebettet — Maus: Drehen=Rechtsklick, Zoom=Rad, Pan=Mitte")
            panel._sb_rahmen("ok")
            panel._sb_status.setText("✅ Vorschau aktiv")
            panel.sandbox_fertig.emit(True, "")

    def _view_zurueckgeben(self):
        """Gibt den eingebetteten View zurück an FreeCAD."""
        if self._vorschau_view_widget is None:
            return
        main_win = self._e.window()
        main_win.setUpdatesEnabled(False)
        try:
            vw = self._vorschau_view_widget
            lay = self._vorschau_container.layout()
            lay.removeWidget(vw)

            # Zurück zum Original-Parent (MdiSubWindow)
            if self._vorschau_orig_parent:
                orig_lay = self._vorschau_orig_parent.layout()
                vw.setParent(self._vorschau_orig_parent)
                if orig_lay:
                    orig_lay.addWidget(vw)
                if self._vorschau_orig_geom:
                    vw.setGeometry(self._vorschau_orig_geom)
                vw.show()
            else:
                # Kein Original-Parent bekannt → als eigenes Fenster zeigen
                vw.setParent(None)
                vw.show()
        except Exception as e:
            self._vorschau_log(f"Rückgabe View: {e}")
        finally:
            main_win.setUpdatesEnabled(True)
            main_win.repaint()
            self._vorschau_view_widget = None
            self._vorschau_orig_parent = None
            self._vorschau_orig_geom   = None
            # Platzhalter wieder anzeigen
            if self._vorschau_placeholder:
                self._vorschau_placeholder.show()
            # Docks wiederherstellen die beim Einbetten versteckt wurden
            for dock, war_sichtbar in getattr(self, "_vorschau_dock_zustaende", []):
                if war_sichtbar and not dock.isVisible():
                    dock.show()
            self._vorschau_dock_zustaende = []

    @staticmethod
    def _hole_view_widget(Gui) -> QtWidgets.QWidget | None:
        """
        Gibt das QWidget des aktiven View3DInventors zurück.
        Versucht mehrere FreeCAD-API-Wege.
        """
        # Weg 1: activeView() direkt
        try:
            doc = Gui.ActiveDocument
            if doc:
                view = doc.ActiveView
                if view and hasattr(view, "graphicsView"):
                    return view.graphicsView()
        except Exception:
            pass

        # Weg 2: getMainWindow → MdiArea → aktives SubWindow → QWidget suchen
        try:
            mw = Gui.getMainWindow()
            mdi = mw.findChild(QtWidgets.QMdiArea)
            if mdi:
                sub = mdi.activeSubWindow()
                if sub:
                    # Das erste QWidget-Kind das kein QMdiSubWindow ist
                    for child in sub.findChildren(QtWidgets.QWidget):
                        cn = type(child).__name__
                        if "View3D" in cn or "Inventor" in cn or "Quarter" in cn:
                            return child
                    # Fallback: den Widget-Inhalt des SubWindows selbst
                    w = sub.widget()
                    if w:
                        return w
        except Exception:
            pass

        # Weg 3: centralWidget des MainWindows
        try:
            mw = Gui.getMainWindow()
            cw = mw.centralWidget()
            if cw:
                for child in cw.findChildren(QtWidgets.QWidget):
                    cn = type(child).__name__
                    if "View3D" in cn or "Inventor" in cn or "Quarter" in cn:
                        return child
        except Exception:
            pass

        return None

    def _vorschau_fit_all(self):
        """fitAll() auf dem aktuellen View."""
        try:
            import FreeCADGui as Gui
            v = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument else None
            if v:
                v.fitAll()
                self._vorschau_status("⊡ fitAll ausgeführt")
        except Exception as e:
            self._vorschau_log(f"fitAll: {e}")

    # ── Tab-Close ────────────────────────────────────────────────────────
    def _vorschau_tab_close_requested(self, index: int):
        if (self._vorschau_widget is not None and
                self._e._editor_tab_widget.widget(index) is self._vorschau_widget):
            self.vorschau_schliessen()

    # ── Hilfsmethoden ────────────────────────────────────────────────────
    def _vorschau_log(self, text: str):
        if self._vorschau_log_box:
            self._vorschau_log_box.appendPlainText(text)
            sb = self._vorschau_log_box.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _vorschau_status(self, text: str, farbe: str = ""):
        if self._vorschau_status_lbl:
            self._vorschau_status_lbl.setText(text)
            self._vorschau_status_lbl.setStyleSheet(
                theme.STY_VORSCHAU_STATUS(schrift.pt(schrift.STUFE_BASE)))

    def _vorschau_fehler_panel_befuellen(self, fehlertext: str) -> None:
        """Lädt den Vorschau-Fehler ins Fehler-Panel (Dock bleibt zu — der
        Zustand ist bereit, wenn der User ihn öffnet). Übersetzen erledigt
        der User dort per 🔍-Button im selben Feld."""
        panel = getattr(self._e, "_fehler_inhalt", None)
        if panel is not None:
            code = getattr(self, "_vorschau_letzter_code", "") or ""
            # _sandbox_ergebnis setzt: Ausgabe, roter Rahmen, KI-Button, Code
            panel._sandbox_ergebnis(False, fehlertext, code)

    def _vorschau_fehler_oeffnen(self) -> None:
        """Öffnet den Fehler-Übersetzer-Dock mit dem letzten Vorschau-Fehler."""
        fehler = getattr(self, "_vorschau_letzter_fehler", None)
        if fehler:
            self._vorschau_fehler_panel_befuellen(fehler)
        if hasattr(self._e, "_dock_fehler"):
            self._e._dock_fehler.show()
            self._e._dock_fehler.raise_()

    def _vorschau_ki_korrigieren(self) -> None:
        """Schickt den fehlgeschlagenen Vorschau-Code + Fehler direkt an die KI."""
        code   = getattr(self, "_vorschau_letzter_code",   None)
        fehler = getattr(self, "_vorschau_letzter_fehler", None)
        if not code or not fehler:
            self._vorschau_status("⚠ Kein Fehler vorhanden zum Korrigieren")
            return
        if not hasattr(self._e, "_on_self_correction_needed"):
            self._vorschau_status("⚠ KI-Korrektur nicht verfügbar")
            return
        self._vorschau_status("🔧 KI korrigiert Vorschau-Fehler …")
        self._vorschau_log("🔧 Sende Fehler an KI zur Korrektur …")
        self._e._on_self_correction_needed(code, fehler)
