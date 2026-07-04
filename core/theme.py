# -*- coding: utf-8 -*-
"""
theme.py  –  Öffentliches API des Design-Systems.

Importiert alles aus den Sub-Modulen.
Bestehender Code (import theme; theme.STY_X) läuft weiterhin unverändert.

Sub-Module:
    theme_schriftanwendung – Emoji-sichere Fonts, apply_global_font
    theme_farbschema       – Farbschema, ist_dunkel, syntax_farben, STY_CODE_EDITOR
    theme_stylesheets      – UI-Texte, Maße, alle anderen STY_* Funktionen
"""

from core.theme_schriftanwendung import *   # noqa: F401, F403
from core.theme_farbschema import *    # noqa: F401, F403
from core.theme_stylesheets import *    # noqa: F401, F403
