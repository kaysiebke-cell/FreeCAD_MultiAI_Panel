# -*- coding: utf-8 -*-
"""
projekt_kontext.py
──────────────────
Projektordner als KI-Kontext — ganze Ordnerbäume statt nur einer Datei.

Zwei Betriebsarten, die sich ergänzen:

  A) Projektkarte  — kompakte Übersicht (Ordnerbaum + AST-Struktur je
     Python-Datei), die bei jedem KI-Aufruf mitgeschickt wird.
     Kostet nur wenige hundert Token statt hunderttausende und
     funktioniert daher auch mit lokalen Ollama-Modellen.

  B) Nachlade-Werkzeuge — die KI holt sich über
     `projekt_dateien_auflisten` / `projekt_datei_lesen` /
     `projekt_suchen` (siehe ki_werkzeuge.py) gezielt genau die Dateien,
     die sie wirklich braucht.

Sicherheit: Alle Pfade werden gegen den gewählten Projektordner geprüft
(`sichere_pfad`). Ausbrüche über „..“ oder Symlinks sind ausgeschlossen,
und es wird ausschließlich gelesen — nie geschrieben.

Dieses Modul ist bewusst frei von Qt- und FreeCAD-Abhängigkeiten, damit
es ohne laufendes FreeCAD getestet werden kann.
"""

from __future__ import annotations

import os

from editor.ki.kod_analyse import erstelle_code_sitemap


# ── Grenzwerte ────────────────────────────────────────────────────────────────

MAX_DATEIEN        = 400       # so viele Dateien wandern höchstens in die Karte
MAX_DATEI_BYTES    = 200_000   # größere Dateien werden übersprungen
MAX_KARTE_ZEICHEN  = 12_000    # harte Obergrenze der fertigen Projektkarte
MAX_LESE_ZEICHEN   = 40_000    # Obergrenze für projekt_datei_lesen
MAX_TREFFER        = 40        # Obergrenze für projekt_suchen

# Ordner, die nie durchsucht werden (Müll, Caches, Fremdcode)
IGNORIER_ORDNER = {
    "__pycache__", ".git", ".hg", ".svn", ".tox", ".venv", "venv", "env",
    "node_modules", "build", "dist", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".idea", ".vscode", ".ipynb_checkpoints", "site-packages",
}

# Endungen, die als Text gelesen werden dürfen
TEXT_ENDUNGEN = {
    ".py", ".pyw", ".fcmacro", ".md", ".txt", ".rst", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".xml", ".html", ".css", ".js", ".sh",
    ".bat", ".ts",
}


# ── Pfad-Absicherung ──────────────────────────────────────────────────────────

def sichere_pfad(wurzel: str, rel_pfad: str) -> str:
    """Löst ``rel_pfad`` innerhalb von ``wurzel`` auf.

    Gibt den absoluten Pfad zurück. Wirft ValueError, wenn der Pfad aus dem
    Projektordner herausführt — egal ob über „..“, einen absoluten Pfad oder
    einen Symlink.
    """
    if not wurzel:
        raise ValueError("Kein Projektordner gewählt.")

    wurzel_abs = os.path.realpath(os.path.expanduser(wurzel))
    if not os.path.isdir(wurzel_abs):
        raise ValueError(f"Projektordner existiert nicht: {wurzel}")

    rel = (rel_pfad or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("Kein Pfad angegeben.")

    # Absolute Pfade sind erlaubt, solange sie im Projektordner liegen —
    # die Prüfung unten weist alles andere ab.
    ziel = os.path.realpath(rel if os.path.isabs(rel)
                            else os.path.join(wurzel_abs, rel))

    if ziel != wurzel_abs and not ziel.startswith(wurzel_abs + os.sep):
        raise ValueError(f"Pfad liegt außerhalb des Projektordners: {rel_pfad}")
    return ziel


# ── Dateien einsammeln ────────────────────────────────────────────────────────

def _ist_textdatei(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in TEXT_ENDUNGEN


def dateien_sammeln(wurzel: str, max_dateien: int = MAX_DATEIEN,
                    max_bytes: int = MAX_DATEI_BYTES) -> list[str]:
    """Sammelt alle Textdateien unterhalb von ``wurzel``.

    Rückgabe: sortierte Liste relativer Pfade mit „/“ als Trenner.
    Ordner aus IGNORIER_ORDNER und zu große Dateien werden ausgelassen.
    """
    wurzel_abs = os.path.realpath(os.path.expanduser(wurzel or ""))
    if not os.path.isdir(wurzel_abs):
        return []

    gefunden: list[str] = []
    for ordner, unterordner, dateien in os.walk(wurzel_abs):
        # In-place filtern, damit os.walk gar nicht erst absteigt
        unterordner[:] = sorted(
            u for u in unterordner
            if u not in IGNORIER_ORDNER and not u.endswith(".egg-info")
        )
        for name in sorted(dateien):
            if not _ist_textdatei(name):
                continue
            voll = os.path.join(ordner, name)
            try:
                if os.path.getsize(voll) > max_bytes:
                    continue
            except OSError:
                continue
            gefunden.append(os.path.relpath(voll, wurzel_abs).replace(os.sep, "/"))
            if len(gefunden) >= max_dateien:
                return sorted(gefunden)
    return sorted(gefunden)


# ── Ordnerbaum zeichnen ───────────────────────────────────────────────────────

def _baum_aufbauen(rel_pfade: list[str]) -> dict:
    baum: dict = {}
    for pfad in rel_pfade:
        knoten = baum
        teile = pfad.split("/")
        for teil in teile[:-1]:
            knoten = knoten.setdefault(teil, {})
        knoten[teile[-1]] = None
    return baum


def _baum_zeichnen(knoten: dict, einzug: str = "") -> list[str]:
    zeilen: list[str] = []
    eintraege = sorted(knoten.items(),
                       key=lambda kv: (kv[1] is None, kv[0].lower()))
    for i, (name, kind) in enumerate(eintraege):
        letzter = (i == len(eintraege) - 1)
        zweig = "└─ " if letzter else "├─ "
        if kind is None:
            zeilen.append(f"{einzug}{zweig}{name}")
        else:
            zeilen.append(f"{einzug}{zweig}{name}/")
            zeilen.extend(_baum_zeichnen(kind, einzug + ("   " if letzter else "│  ")))
    return zeilen


def ordnerbaum(wurzel: str, rel_pfade: list[str]) -> str:
    """Zeichnet den Ordnerbaum der übergebenen relativen Pfade."""
    if not rel_pfade:
        return "(keine lesbaren Dateien gefunden)"
    kopf = os.path.basename(os.path.normpath(wurzel)) or wurzel
    return "\n".join([f"{kopf}/"] + _baum_zeichnen(_baum_aufbauen(rel_pfade)))


# ── Projektkarte ──────────────────────────────────────────────────────────────

# AST-Parsen ist der teuerste Teil der Karte. Ergebnisse werden je Datei
# gemerkt und nur bei geänderter Größe/Änderungszeit neu berechnet — sonst
# würde jede KI-Anfrage das ganze Projekt erneut parsen.
_SITEMAP_CACHE: dict[str, tuple[float, int, str]] = {}
_CACHE_MAX = 2_000


def _sitemap_fuer_datei(voll_pfad: str) -> str:
    """AST-Inhaltsverzeichnis einer Datei, gepuffert über mtime und Größe."""
    try:
        stat = os.stat(voll_pfad)
    except OSError:
        return ""

    gemerkt = _SITEMAP_CACHE.get(voll_pfad)
    if gemerkt and gemerkt[0] == stat.st_mtime and gemerkt[1] == stat.st_size:
        return gemerkt[2]

    try:
        with open(voll_pfad, encoding="utf-8", errors="replace") as f:
            sitemap = erstelle_code_sitemap(f.read())
    except OSError:
        return ""

    if len(_SITEMAP_CACHE) >= _CACHE_MAX:
        _SITEMAP_CACHE.clear()
    _SITEMAP_CACHE[voll_pfad] = (stat.st_mtime, stat.st_size, sitemap)
    return sitemap


def _sitemap_block(wurzel: str, rel_pfade: list[str]) -> list[str]:
    """Erzeugt je Python-Datei ein AST-Inhaltsverzeichnis."""
    bloecke: list[str] = []
    for rel in rel_pfade:
        if not rel.lower().endswith((".py", ".pyw", ".fcmacro")):
            continue
        sitemap = _sitemap_fuer_datei(os.path.join(wurzel, rel))
        if not sitemap:
            continue
        eingerueckt = "\n".join(f"   {z}" for z in sitemap.splitlines())
        bloecke.append(f"{rel}\n{eingerueckt}")
    return bloecke


def erstelle_projektkarte(wurzel: str,
                          max_dateien: int = MAX_DATEIEN,
                          max_zeichen: int = MAX_KARTE_ZEICHEN,
                          mit_struktur: bool = True) -> str:
    """Baut die kompakte Projektübersicht für den Prompt.

    Enthält Ordnerbaum und die Struktur (Klassen/Funktionen) aller
    Python-Dateien — aber keinen Quelltext. Gibt "" zurück, wenn der Ordner
    leer oder nicht lesbar ist.

    ``mit_struktur=False`` liefert nur den Ordnerbaum — deutlich sparsamer
    und damit die richtige Wahl für lokale Modelle mit kleinem Kontext.
    """
    wurzel_abs = os.path.realpath(os.path.expanduser(wurzel or ""))
    if not os.path.isdir(wurzel_abs):
        return ""

    rel_pfade = dateien_sammeln(wurzel_abs, max_dateien=max_dateien)
    if not rel_pfade:
        return ""

    kopf = (f"Projektordner: {wurzel_abs}\n"
            f"Dateien: {len(rel_pfade)}"
            f"{' (gekürzt)' if len(rel_pfade) >= max_dateien else ''}\n\n"
            f"{ordnerbaum(wurzel_abs, rel_pfade)}")

    bloecke = _sitemap_block(wurzel_abs, rel_pfade) if mit_struktur else []
    if not bloecke:
        return kopf[:max_zeichen]

    teile = [kopf, "", "Struktur der Python-Dateien:"]
    laenge = sum(len(t) + 1 for t in teile)
    for block in bloecke:
        if laenge + len(block) + 1 > max_zeichen:
            teile.append("… (weitere Dateien gekürzt — "
                         "bei Bedarf projekt_datei_lesen verwenden)")
            break
        teile.append(block)
        laenge += len(block) + 1
    return "\n".join(teile)


def karte_als_prompt_block(wurzel: str, kompakt: bool = False) -> str:
    """Projektkarte fertig umrahmt für den Prompt — "" wenn nichts vorliegt.

    ``kompakt=True`` (für Ollama & Co.): nur Ordnerbaum, halbes Zeichenlimit.
    """
    if kompakt:
        karte = erstelle_projektkarte(wurzel,
                                      max_zeichen=MAX_KARTE_ZEICHEN // 3,
                                      mit_struktur=False)
    else:
        karte = erstelle_projektkarte(wurzel)
    if not karte:
        return ""
    return (
        "━━━ PROJEKTORDNER (Übersicht, kein Quelltext) ━━━\n"
        f"{karte}\n"
        "Hinweis: Der Quelltext einzelner Dateien ist NICHT enthalten. "
        "Frage gezielt nach einer Datei, wenn du ihren Inhalt brauchst.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


# ── Nachladen: lesen und suchen ───────────────────────────────────────────────

def datei_lesen(wurzel: str, rel_pfad: str,
                max_zeichen: int = MAX_LESE_ZEICHEN) -> str:
    """Liest eine einzelne Projektdatei mit Zeilennummern.

    Wirft ValueError bei Pfaden außerhalb des Projektordners, fehlenden
    Dateien oder nicht unterstützten Dateitypen.
    """
    ziel = sichere_pfad(wurzel, rel_pfad)
    if not os.path.isfile(ziel):
        raise ValueError(f"Datei nicht gefunden: {rel_pfad}")
    if not _ist_textdatei(os.path.basename(ziel)):
        raise ValueError(f"Kein unterstütztes Textformat: {rel_pfad}")

    with open(ziel, encoding="utf-8", errors="replace") as f:
        inhalt = f.read()

    gekuerzt = len(inhalt) > max_zeichen
    if gekuerzt:
        inhalt = inhalt[:max_zeichen]

    zeilen = [f"{nr:5d}: {text}"
              for nr, text in enumerate(inhalt.splitlines(), 1)]
    if gekuerzt:
        zeilen.append(f"… (gekürzt bei {max_zeichen} Zeichen)")
    return "\n".join(zeilen)


def projekt_suchen(wurzel: str, muster: str,
                   max_treffer: int = MAX_TREFFER) -> str:
    """Sucht ``muster`` (Klartext, Groß-/Kleinschreibung egal) im Projekt.

    Rückgabe: Zeilen der Form ``pfad:zeilennummer: inhalt``.
    """
    if not (muster or "").strip():
        raise ValueError("Suchmuster ist leer.")

    wurzel_abs = os.path.realpath(os.path.expanduser(wurzel or ""))
    if not os.path.isdir(wurzel_abs):
        raise ValueError(f"Projektordner existiert nicht: {wurzel}")

    nadel = muster.lower()
    treffer: list[str] = []
    for rel in dateien_sammeln(wurzel_abs):
        try:
            with open(os.path.join(wurzel_abs, rel), encoding="utf-8",
                      errors="replace") as f:
                for nr, zeile in enumerate(f, 1):
                    if nadel in zeile.lower():
                        treffer.append(f"{rel}:{nr}: {zeile.rstrip()[:200]}")
                        if len(treffer) >= max_treffer:
                            treffer.append(
                                f"… (bei {max_treffer} Treffern abgebrochen)")
                            return "\n".join(treffer)
        except OSError:
            continue
    return "\n".join(treffer) if treffer else f"Keine Treffer für '{muster}'."


# ── Statistik für die Oberfläche ──────────────────────────────────────────────

def schaetze_tokens(text: str) -> int:
    """Grobe Token-Schätzung (~4 Zeichen je Token)."""
    return len(text) // 4


def projekt_statistik(wurzel: str) -> tuple[int, int]:
    """Gibt (Anzahl Dateien, geschätzte Token der Projektkarte) zurück."""
    karte = erstelle_projektkarte(wurzel)
    if not karte:
        return 0, 0
    return len(dateien_sammeln(wurzel)), schaetze_tokens(karte)
