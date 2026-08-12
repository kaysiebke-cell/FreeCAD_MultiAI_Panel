# -*- coding: utf-8 -*-
"""
projekt_nachladen.py
────────────────────
Die KI holt sich Projektdateien selbst nach.

Mit der Projektkarte (siehe projekt_kontext.py) kennt das Modell die
Struktur des Projekts, aber keinen Quelltext. Braucht es den Inhalt einer
Datei, antwortet es mit Anforderungszeilen:

    #DATEI: core/params.py
    #SUCHE: Placement

Dieses Modul erkennt solche Zeilen nach dem Stream-Ende, liest die Dateien
(abgesichert über projekt_kontext.sichere_pfad), hängt sie an den
Gesprächsverlauf an und startet die Anfrage automatisch neu — das Modell
antwortet dann mit dem Wissen aus den Dateien.

Der Umweg über Textmarken statt echter Tool-Call-APIs ist Absicht: so
funktioniert das Nachladen mit allen 19 Anbietern, auch mit lokalen
Ollama-Modellen ohne Tool-Unterstützung.

Die reinen Funktionen (`finde_anforderungen`, `baue_nachlade_block`) sind
frei von Qt und FreeCAD und damit ohne laufendes FreeCAD testbar.
"""

from __future__ import annotations

import re

from editor.ki.projekt_kontext import MAX_LESE_ZEICHEN, datei_lesen, projekt_suchen

# Höchstens so viele Dateien/Suchen je Runde …
MAX_ANFORDERUNGEN = 3
# … und höchstens so viele Nachlade-Runden je Frage (Schutz vor Endlosschleifen)
MAX_RUNDEN = 2
# Kürzeres Limit als beim direkten Lesen — es können mehrere Dateien sein
MAX_ZEICHEN_JE_DATEI = MAX_LESE_ZEICHEN // 2

_RE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_RE_ANFORDERUNG = re.compile(
    r"^[ \t]*#[ \t]*(DATEI|SUCHE)[ \t]*:[ \t]*(.+?)[ \t]*$",
    re.MULTILINE | re.IGNORECASE)

ANFORDERUNGS_HINWEIS = (
    "Wenn du den Inhalt einer Datei brauchst, antworte NUR mit "
    "Anforderungszeilen (nichts sonst):\n"
    "  #DATEI: relativer/pfad.py    → liefert den Dateiinhalt\n"
    "  #SUCHE: suchbegriff          → liefert Fundstellen im Projekt\n"
    f"Höchstens {MAX_ANFORDERUNGEN} Zeilen pro Antwort. Du bekommst das "
    "Ergebnis automatisch und antwortest danach ganz normal.\n"
)


# ── Reine Logik ───────────────────────────────────────────────────────────────

def finde_anforderungen(text: str) -> list[tuple[str, str]]:
    """Sucht Anforderungszeilen in einer KI-Antwort.

    Rückgabe: Liste aus ("datei"|"suche", Argument), höchstens
    MAX_ANFORDERUNGEN Einträge, Duplikate entfernt. Codeblöcke in ``` ```
    werden vorher entfernt, damit ein Kommentar im generierten Code keine
    Anforderung auslöst.
    """
    ohne_code = _RE_FENCE.sub("", text or "")

    gefunden: list[tuple[str, str]] = []
    gesehen: set[tuple[str, str]] = set()
    for art, wert in _RE_ANFORDERUNG.findall(ohne_code):
        eintrag = (art.lower(), wert.strip().strip("\"'`"))
        if not eintrag[1] or eintrag in gesehen:
            continue
        gesehen.add(eintrag)
        gefunden.append(eintrag)
        if len(gefunden) >= MAX_ANFORDERUNGEN:
            break
    return gefunden


def baue_nachlade_block(wurzel: str,
                        anforderungen: list[tuple[str, str]]) -> str:
    """Löst die Anforderungen auf und baut den Text für die Folgeanfrage."""
    teile: list[str] = []
    for art, wert in anforderungen:
        try:
            if art == "datei":
                inhalt = datei_lesen(wurzel, wert,
                                     max_zeichen=MAX_ZEICHEN_JE_DATEI)
                teile.append(f"── Datei: {wert} ──\n{inhalt}")
            else:
                inhalt = projekt_suchen(wurzel, wert)
                teile.append(f"── Suche: {wert} ──\n{inhalt}")
        except ValueError as exc:
            teile.append(f"── {wert} ──\n(nicht verfügbar: {exc})")
        except Exception as exc:  # defekte Datei, Rechte, …
            teile.append(f"── {wert} ──\n(Fehler beim Lesen: {exc})")

    if not teile:
        return ""
    return (
        "Angeforderte Projektinhalte:\n"
        + "\n\n".join(teile)
        + "\n\nBeantworte jetzt die ursprüngliche Frage. "
          "Fordere nichts erneut an, wenn es oben bereits steht."
    )


def kurzfassung(anforderungen: list[tuple[str, str]]) -> str:
    """Statuszeile für die Oberfläche."""
    return ", ".join(w for _, w in anforderungen)


# ── Anbindung an den Editor ───────────────────────────────────────────────────

def nachladen_falls_angefordert(controller, antwort: str) -> bool:
    """Prüft die Antwort auf Anforderungen und startet ggf. die Folgeanfrage.

    Gibt True zurück, wenn eine Folgeanfrage läuft — der Aufrufer soll die
    Antwort dann nicht als Endergebnis behandeln.
    """
    # Nur wenn die Anfrage das Protokoll überhaupt angeboten hat
    if not getattr(controller, "_projekt_nachlade_erlaubt", False):
        return False

    anforderungen = finde_anforderungen(antwort)
    if not anforderungen:
        controller._projekt_nachlade_runde = 0
        return False

    try:
        from core.params import lade_projektordner
        wurzel = lade_projektordner()
    except Exception:
        wurzel = ""
    if not wurzel:
        return False

    runde = getattr(controller, "_projekt_nachlade_runde", 0) + 1
    if runde > MAX_RUNDEN:
        controller._projekt_nachlade_runde = 0
        controller._set_status(
            f"⚠  Nachladen nach {MAX_RUNDEN} Runden gestoppt – "
            "Frage bitte konkreter stellen")
        return False

    block = baue_nachlade_block(wurzel, anforderungen)
    if not block:
        controller._projekt_nachlade_runde = 0
        return False

    controller._projekt_nachlade_runde = runde
    controller._chat_verlauf.append({"role": "assistant", "content": antwort.strip()})
    controller._chat_verlauf.append({"role": "user", "content": block})

    controller._set_status(
        f"📂 Lade nach (Runde {runde}/{MAX_RUNDEN}): "
        f"{kurzfassung(anforderungen)}")
    _folgeanfrage_starten(controller)
    return True


def _folgeanfrage_starten(controller) -> None:
    """Startet denselben Worker wie eine normale Chat-Anfrage neu."""
    import threading
    import time

    controller._ki_lauf_ui(True)
    controller._btn_ersetzen.setEnabled(False)
    controller._ki_area.clear()
    controller._chunk_buffer.clear()
    controller._stream_token_count = 0
    controller._warte_dots = 0
    controller._warte_aktiv = True
    controller._stream_start_time = time.monotonic()
    controller._flush_timer.start()
    controller._status_timer.start()
    if hasattr(controller, "_warte_timer"):
        controller._warte_timer.start()

    threading.Thread(
        target=controller._streaming.worker_mit_verlauf,
        args=(controller._src_box.currentText(),
              controller._model_box.currentText(),
              list(controller._chat_verlauf),
              controller._temp_box.value()),
        daemon=True
    ).start()
