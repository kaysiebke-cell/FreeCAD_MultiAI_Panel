# -*- coding: utf-8 -*-
"""
hilfe.py
────────
HilfeTab – aufklappbare Hilfe-Dokumentation als QWidget.

Texte werden aus hilfe_texte.py importiert.

Verwendung:
    from hilfe import HilfeTab
    left_tabs.addTab(HilfeTab(), "❓ Hilfe")
"""

from core.qt_compat import QtWidgets, QtCore, QtGui
from core import theme
from core import schrift
from data.hilfe_texte import HILFE_ABSCHNITTE


class HilfeTab(QtWidgets.QWidget):
    """Aufklappbare Hilfe-Dokumentation als eigenständiges QWidget."""

    _FARBEN = theme.HILFE_FARBEN
    _FARBE_DEFAULT = theme.HILFE_FARBE_DEFAULT

    _STY_BODY = theme.STY_HILFE_BODY

    def __init__(self, parent=None, zusaetze: dict | None = None):
        """zusaetze: {Titel-Präfix: Text} — wird dem passenden Abschnitt
        vorangestellt (z.B. generierte Shortcut-Übersicht aus der
        Aktions-Registry)."""
        super().__init__(parent)
        self._zusaetze = zusaetze or {}
        self._ui_font = schrift.ui_font()
        try:
            from main import emoji_font
            self._ui_font = emoji_font(self._ui_font)
        except Exception:
            pass
        self.setFont(self._ui_font)
        self.setObjectName("HilfeTab")
        self.setStyleSheet(theme.STY_HILFE_TAB)
        self._mono_font = schrift.mono_font()
        try:
            from main import emoji_font
            self._mono_font = emoji_font(self._mono_font)
        except Exception:
            pass
        self._alle_widgets: list = []
        self._baue_ui()

    def _baue_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(theme.ABST_M, theme.ABST_L, theme.ABST_M, theme.ABST_M)
        layout.setSpacing(theme.ABST_M)

        such_zeile = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel(theme.TEXTS["hilfe_suche_icon"])
        icon.setFont(self._ui_font)
        icon.setStyleSheet(theme.STY_ICON_BTN_BORDERLESS(schrift.pt(schrift.STUFE_XL)))
        such_zeile.addWidget(icon)
        self._suche = QtWidgets.QLineEdit()
        self._suche.setFont(self._ui_font)
        self._suche.setPlaceholderText(theme.TEXTS["hilfe_suche_placeholder"])
        self._suche.setClearButtonEnabled(True)
        self._suche.setStyleSheet(theme.STY_HILFE_SUCHE)
        such_zeile.addWidget(self._suche)
        layout.addLayout(such_zeile)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setContentsMargins(theme.ABST_XS, theme.ABST_XS, theme.ABST_XS, theme.ABST_XL)
        vbox.setSpacing(theme.ABST_S)

        for titel, inhalt in HILFE_ABSCHNITTE:
            for praefix, zusatz in self._zusaetze.items():
                if titel.startswith(praefix):
                    inhalt = f"{zusatz}\n\n{inhalt}"
                    break
            akzent, bg = self._akzent(titel)
            vbox.addWidget(self._baue_abschnitt(titel, inhalt, akzent, bg))

        vbox.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        ver = QtWidgets.QLabel(theme.TEXTS["hilfe_version_label"])
        ver.setFont(self._ui_font)
        ver.setAlignment(QtCore.Qt.AlignCenter)
        ver.setStyleSheet(theme.STY_VERSION_LABEL())
        layout.addWidget(ver)

        self._suche.textChanged.connect(self._filtern)

    def _baue_abschnitt(self, titel: str, inhalt: str,
                        akzent: str, bg: str) -> QtWidgets.QWidget:
        abschnitt = QtWidgets.QWidget()
        av = QtWidgets.QVBoxLayout(abschnitt)
        av.setContentsMargins(theme.ABST_KEIN, theme.ABST_KEIN, theme.ABST_KEIN, theme.ABST_KEIN)
        av.setSpacing(theme.ABST_KEIN)

        btn = QtWidgets.QPushButton(f"▶  {titel.replace('&', '&&')}")
        btn.setCheckable(True)
        btn.setFont(self._ui_font)
        btn.setStyleSheet(theme.STY_SECTION_HEAD_BTN(schrift.pt(schrift.STUFE_LG)))

        # QLabel statt QPlainTextEdit: heightForWidth() regelt Höhe automatisch,
        # kein manueller setFixedHeight-Hack nötig.
        lbl = QtWidgets.QLabel()
        lbl.setFont(self._mono_font)
        lbl.setWordWrap(True)
        lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        lbl.setText(inhalt)
        lbl.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        lbl.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
            | QtCore.Qt.TextSelectableByKeyboard)
        lbl.setStyleSheet(self._STY_BODY)
        lbl.setVisible(False)

        def _toggle(checked, b=btn, l=lbl):
            l.setVisible(checked)
            b.setText(("▼" if checked else "▶") + b.text()[1:])

        btn.toggled.connect(_toggle)
        av.addWidget(btn)
        av.addWidget(lbl)
        self._alle_widgets.append(
            (abschnitt, btn, lbl, titel.lower(), inhalt.lower()))
        return abschnitt

    def _akzent(self, titel: str) -> tuple[str, str]:
        for prefix, farbe, bg in self._FARBEN:
            if titel.startswith(prefix):
                return farbe, bg
        return self._FARBE_DEFAULT

    def _filtern(self, text: str):
        begriffe = text.lower().split()
        for abschnitt, btn, lbl, titel_l, inhalt_l in self._alle_widgets:
            if not begriffe:
                abschnitt.setVisible(True)
                btn.setChecked(False)
            else:
                treffer = all(b in titel_l or b in inhalt_l for b in begriffe)
                abschnitt.setVisible(treffer)
                if treffer:
                    btn.setChecked(True)
