# -*- coding: utf-8 -*-
"""
sprach_kern.py  (PROTOTYP)
──────────────────────────
Lokaler Kern der Sprachsteuerung — komplett offline, ohne externen Anbieter:

  1. BefehlsGrammatik  – ordnet erkannten Text einer registrierten Aktion zu
  2. SprachWorker      – nimmt das Mikrofon auf und erkennt Text mit Vosk
  3. sprich()          – Sprachausgabe (optional)

Aufnahme über parec / pw-record / ffmpeg (PulseAudio/PipeWire) — bewusst NICHT
über sounddevice/PortAudio, weil PortAudio im FreeCAD-Flatpak fehlt. So läuft
die Aufnahme im Flatpak genauso wie in einem nativen FreeCAD.

  pip install vosk        # nur Vosk nötig (Aufnahme via Systemtool)
  Modell (deutsch, ~50 MB):
    https://alphacephei.com/vosk/models  →  vosk-model-small-de-0.15
"""

from __future__ import annotations
import os
import re
import json
import shutil
import subprocess

from core.qt_compat import QtCore

# ── Optionale Engines ───────────────────────────────────────────────────────
try:
    import vosk           # noqa: F401
    HAS_VOSK = True
except Exception:
    HAS_VOSK = False

try:
    import faster_whisper  # noqa: F401
    HAS_WHISPER = True
except Exception:
    HAS_WHISPER = False


# ════════════════════════════════════════════════════════════════════════════
# 1) Befehls-Grammatik  —  Text → Aktionsname
# ════════════════════════════════════════════════════════════════════════════

_STOPWORTE = {
    "der", "die", "das", "den", "dem", "ein", "eine", "und", "oder", "mal",
    "bitte", "mir", "mich", "zum", "zur", "auf", "im", "in", "los", "jetzt",
}

_SYNONYME: dict[str, list[str]] = {
    "speichern":          ["speichern", "speicher", "sichern", "abspeichern"],
    "ausfuehren":         ["ausführen", "starten", "starte", "laufen", "ausführung"],
    "auswahl_ausfuehren": ["auswahl", "markierung", "markierte", "selektion"],
    "suche":              ["suche", "suchen", "finde", "finden", "suchleiste"],
    "suche_weiter":       ["weiter", "weitersuchen", "nächster", "nächste"],
    "neu_laden":          ["neu laden", "neuladen", "zurücksetzen", "verwerfen"],
    "ki_fragen":          ["assistent", "frage", "fragen", "frag", "ki fragen"],
    "formatieren":        ["formatieren", "formatiere", "einrücken", "aufräumen"],
    "hilfe":              ["hilfe", "hilf", "anleitung"],
}


def _normalisieren(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zäöüß ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def aehnlich(a: str, b: str, schwelle: float = 0.82) -> bool:
    """Unscharfer Wortvergleich (Levenshtein-Ähnlichkeit) — fängt Aussprache-/
    Dialekt-/Erkennungsvarianten ab: „schliese"≈„schließe", „datein"≈„dateien".
    Nur für längere Wörter (kurze wie „ja/da" wären sonst zu leicht verwechselt)."""
    if len(a) < 4 or len(b) < 4:
        return a == b
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() >= schwelle


class BefehlsGrammatik:
    """Text → beste registrierte Aktion — rein lokal, kein Sprachmodell nötig."""

    def __init__(self, phrasen_je_aktion: dict[str, list[str]]):
        self._map = phrasen_je_aktion

    @classmethod
    def aus_registry(cls, aktionen) -> "BefehlsGrammatik":
        registry = getattr(aktionen, "_aktionen", {}) or {}
        phrasen: dict[str, list[str]] = {}
        for name, akt in registry.items():
            woerter = set(_SYNONYME.get(name, []))
            for w in _normalisieren(akt.text()).split():
                if len(w) > 2 and w not in _STOPWORTE:
                    woerter.add(w)
            if woerter:
                phrasen[name] = sorted(woerter)
        return cls(phrasen)

    def finde_aktion(self, text: str) -> tuple[str | None, int]:
        t = _normalisieren(text)
        if not t:
            return None, 0
        woerter = t.split()
        best, best_score = None, 0
        for name, phrasen in self._map.items():
            score = 0
            for p in phrasen:
                if " " in p:
                    if p in t:
                        score += 2
                else:
                    if any(w == p or (len(p) >= 4 and p in w) or aehnlich(w, p)
                           for w in woerter):
                        score += 1
            if score > best_score:
                best, best_score = name, score
        return best, best_score

    def alle_beispiele(self) -> list[str]:
        gesehen: list[str] = []
        for ph in self._map.values():
            if ph and ph[0] not in gesehen:
                gesehen.append(ph[0])
        return gesehen


# ════════════════════════════════════════════════════════════════════════════
# 2) Vosk-Erkennung  (Aufnahme via Systemtool, Push-frei / auto-Stopp)
# ════════════════════════════════════════════════════════════════════════════

def finde_vosk_modell() -> str | None:
    kandidaten = [
        os.environ.get("VOSK_MODEL_DE", ""),
        # großes Modell bevorzugen (genauer fürs Diktat), falls vorhanden
        os.path.expanduser("~/.cache/vosk/vosk-model-de-0.21"),
        os.path.expanduser("~/.cache/vosk/vosk-model-small-de-0.15"),
        os.path.expanduser("~/.local/share/vosk/vosk-model-small-de-0.15"),
        os.path.expanduser("~/vosk-model-small-de-0.15"),
    ]
    for k in kandidaten:
        if k and os.path.isdir(k):
            return k
    return None


# Modell EINMALIG laden und behalten — das große Modell braucht ~16 s;
# ohne Cache würde jeder „Zuhören"-Start neu laden.
_MODELL_CACHE: dict[str, object] = {}


def lade_modell(pfad: str):
    m = _MODELL_CACHE.get(pfad)
    if m is None:
        import vosk
        vosk.SetLogLevel(-1)
        m = vosk.Model(pfad)
        _MODELL_CACHE[pfad] = m
    return m


_WHISPER_CACHE: dict[str, object] = {}


def lade_whisper(groesse: str = "small"):
    """Lädt (und lädt beim ersten Mal herunter) ein faster-whisper-Modell,
    gecacht. „small" ist ein guter Kompromiss aus Genauigkeit und Tempo."""
    m = _WHISPER_CACHE.get(groesse)
    if m is None:
        from faster_whisper import WhisperModel
        m = WhisperModel(groesse, device="cpu", compute_type="int8")
        _WHISPER_CACHE[groesse] = m
    return m


class ModellLader(QtCore.QThread):
    """Lädt das gewählte Modell einmalig im Hintergrund vor (kein GUI-Freeze)."""
    fertig = QtCore.Signal()

    def __init__(self, lade_fn, parent=None):
        super().__init__(parent)
        self._fn = lade_fn

    def run(self):
        try:
            self._fn()
        except Exception:
            pass
        self.fertig.emit()


def recorder_cmd() -> list[str] | None:
    """Kommando, das rohes 16 kHz Mono s16le auf stdout schreibt.
    parec (PulseAudio) › pw-record (PipeWire) › ffmpeg — kein PortAudio."""
    if shutil.which("parec"):
        return ["parec", "--format=s16le", "--rate=16000", "--channels=1", "--raw"]
    if shutil.which("pw-record"):
        return ["pw-record", "--rate=16000", "--channels=1", "--format=s16", "-"]
    if shutil.which("ffmpeg"):
        return ["ffmpeg", "-loglevel", "quiet", "-f", "pulse", "-i", "default",
                "-ar", "16000", "-ac", "1", "-f", "s16le", "-"]
    return None


def aufnahme_moeglich() -> bool:
    return recorder_cmd() is not None


class SprachWorker(QtCore.QThread):
    """Hört zu und stoppt AUTOMATISCH bei der Sprechpause (Vosk erkennt das
    Äußerungsende). Kein Tastenhalten. Aufnahme über Systemtool-Subprozess."""

    erkannt = QtCore.Signal(str)
    fehler  = QtCore.Signal(str)
    pegel   = QtCore.Signal(float)   # 0.0–1.0 Mikrofonpegel („ich höre dich")

    def __init__(self, modell_pfad: str, grammatik: str | None = None,
                 engine: str = "vosk", whisper_groesse: str = "small",
                 hint: str | None = None, parent=None):
        super().__init__(parent)
        self._modell_pfad = modell_pfad
        self._grammatik = grammatik      # Vosk: JSON-Wortliste (Befehlsmodus)
        self._engine = engine            # "vosk" | "whisper"
        self._whisper_groesse = whisper_groesse
        self._hint = hint                # Whisper: Vokabular-Bias (Befehlsmodus)
        self._stop = False
        self._proc = None

    def stoppen(self):
        self._stop = True
        p = self._proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass

    def _pegel_von(self, data: bytes) -> float:
        """RMS-Pegel (0..1) berechnen + für die „ich höre dich"-Anzeige senden."""
        try:
            import array, math
            a = array.array("h"); a.frombytes(data)
            if not a:
                return 0.0
            rms = math.sqrt(sum(x * x for x in a) / len(a)) / 32768.0
            lvl = min(1.0, rms * 4.0)
            self.pegel.emit(lvl)
            return lvl
        except Exception:
            return 0.0

    def run(self):
        cmd = recorder_cmd()
        if cmd is None:
            self.fehler.emit("Kein Aufnahme-Tool gefunden (parec/pw-record/ffmpeg).")
            return
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if self._engine == "whisper" and HAS_WHISPER:
                self._run_whisper()
            else:
                self._run_vosk()
        except Exception as e:
            self.fehler.emit(str(e))
        finally:
            p = self._proc
            if p and p.poll() is None:
                try:
                    p.terminate()
                    p.wait(1)
                except Exception:
                    pass
            self._proc = None

    def _run_vosk(self):
        import vosk
        modell = lade_modell(self._modell_pfad)   # aus dem Cache
        if self._grammatik:
            rec = vosk.KaldiRecognizer(modell, 16000, self._grammatik)
        else:
            rec = vosk.KaldiRecognizer(modell, 16000)
        ergebnis = ""
        while not self._stop:
            data = self._proc.stdout.read(4000)
            if not data:
                break
            self._pegel_von(data)
            if rec.AcceptWaveform(data):          # Sprechpause → Äußerung fertig
                t = json.loads(rec.Result()).get("text", "").strip()
                if t:
                    ergebnis = t
                    break
        if not ergebnis:
            ergebnis = json.loads(rec.FinalResult()).get("text", "").strip()
        self.erkannt.emit(ergebnis)

    def _run_whisper(self):
        """Nimmt eine Äußerung auf (eigene Sprechpausen-Erkennung über den
        Pegel), transkribiert sie dann mit faster-whisper — genauer bei
        Akzent/Dialekt, dafür etwas langsamer."""
        import numpy as np
        modell = lade_whisper(self._whisper_groesse)   # aus dem Cache
        puffer = bytearray()
        begonnen = False
        stille = 0
        max_bytes = 16000 * 2 * 20   # 20 s Sicherheitslimit
        while not self._stop:
            data = self._proc.stdout.read(4000)   # ~0,125 s
            if not data:
                break
            lvl = self._pegel_von(data)
            if lvl > 0.06:                # Sprache
                begonnen = True
                stille = 0
                puffer += data
            elif begonnen:               # Stille nach Sprache
                puffer += data
                stille += 1
                if stille >= 6:          # ~0,75 s Pause → Äußerung fertig
                    break
            if len(puffer) > max_bytes:
                break
        if self._stop or not puffer:
            self.erkannt.emit("")
            return
        audio = np.frombuffer(bytes(puffer), dtype=np.int16).astype(np.float32) / 32768.0
        segmente, _info = modell.transcribe(
            audio, language="de", beam_size=1, vad_filter=False,
            initial_prompt=self._hint or None)
        text = " ".join(s.text for s in segmente).strip()
        self.erkannt.emit(text)


# ════════════════════════════════════════════════════════════════════════════
# 3) Sprachausgabe (optional, lokal)
# ════════════════════════════════════════════════════════════════════════════

def sprich(text: str) -> None:
    if not text:
        return
    if shutil.which("espeak-ng"):
        try:
            subprocess.Popen(["espeak-ng", "-v", "de", text],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
