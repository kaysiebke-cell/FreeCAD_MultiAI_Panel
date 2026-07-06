[← Prev: Feature Overview](feature-overview.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)

# Voice Control (local & offline)

Operate the workbench **by voice** — navigate panels, trigger actions, and dictate text into the editor or the AI question field. Everything runs **locally and offline** (Vosk speech recognition + PulseAudio capture) — no external provider, no API key, nothing leaves your computer. Built with accessibility as the priority.

Open it via the **🎤 Sprache** toolbar button.

## Setup

Two recognition engines are supported (switch with the **🎯 Genauer (Whisper)** checkbox in the panel):

```bash
pip install vosk             # fast engine (small footprint)
pip install faster-whisper   # accurate engine — much better with accents/dialects
```
Recording uses the system tool `parec` / `pw-record` (no PortAudio needed).

- **Vosk** — German model into `~/.cache/vosk/`: small `vosk-model-small-de-0.15` (~45 MB) or large `vosk-model-de-0.21` (~1.9 GB, preferred).
- **Whisper** — the `small` model is downloaded automatically on first use (~0.5 GB, cached). This is the **default** when `faster-whisper` is installed, because it handles individual pronunciation and dialects far better.
- **Flatpak:** FreeCAD needs microphone access (`--socket=pulseaudio`, usually already granted).
- Without a model you can still **type** commands into the panel's text field.

## Start listening

- Click **🎤 Zuhören** or press **F4** — speak, then pause; recognition **stops automatically** at the pause. No key to hold down.
- **Freihand** checkbox — keeps listening after each command for fully hands-free use.
- The **level bar** moves when the microphone picks you up ("I hear you").
- The model is loaded **once in the background** when the panel opens (large model ~15 s → status "Bereit"), after that every start is instant.

## Modes — three big buttons

Instead of a dropdown (which needs open-then-select), the mode is chosen with **one** large, always-visible button:

- **🧭 Befehle** — control panels & actions
- **✍ Editor** — dictate text into the code editor
- **✍ KI** — dictate into the AI question field

Switch by clicking a button, or by voice: "diktat editor" · "diktat ki" · "befehle".

## Commands (Befehle mode)

- **Panels:** "öffne/schließe Dateien | KI | Einstellungen | Fehler | Tools | Werkzeuge …"
- **Actions:** "speichern · ausführen · suche · formatieren · hilfe · KI fragen · auswahl ausführen"
- **"stop"** aborts a running execution / AI request (or stops listening)
- **"rückgängig"** = undo (Ctrl+Z)
- **Risky actions** ("neu laden", "ausführen") ask first → say **"ja"** to confirm, "nein" to cancel. This protects against misrecognition.

## Dictation (Editor / KI mode)

- Spoken words are inserted as text at the cursor.
- **Punctuation words:** "neue zeile" (line break), "punkt", "komma", "fragezeichen", "doppelpunkt", "klammer auf/zu", "leerzeichen" …
- **"lösche"** removes the last word — voice correction, no keyboard needed.
- **"abschicken"** (KI mode) sends the dictated question straight to the AI.

## Accuracy

- **Engine choice:** **Whisper** (default, if installed) handles individual pronunciation, accents and German dialects far better than **Vosk** — Vosk is faster but less robust. Switch anytime with the 🎯 checkbox.
- In **Befehle** mode the recognition is biased toward the **known command vocabulary** (a hard word list for Vosk, a prompt hint for Whisper), so command misrecognitions are rare.
- On top of that, commands and panel names use **fuzzy matching** — near-misses still hit the right command (e.g. "schliese"/"schlisse" → *schließen*, "ausfüren" → *ausführen*). Great for dialects and slightly-off recognition.
- **Dictation** (free text) benefits most from Whisper or the large Vosk model.
- Neither engine is trained on *your personal* voice — accuracy comes from the engine, the vocabulary bias, and fuzzy matching, not from a per-user training step.

## Notes & limits

- Speak clearly, keep a short pause at the end, and use a quiet room — small models are most confused by background noise.
- Abort/stop takes effect at the next recognized utterance.
- Requires `parec`/`pw-record`/`ffmpeg` (present on PipeWire/PulseAudio systems). PortAudio/`sounddevice` is intentionally **not** used because it is missing in the FreeCAD Flatpak.

---

[← Prev: Feature Overview](feature-overview.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)
