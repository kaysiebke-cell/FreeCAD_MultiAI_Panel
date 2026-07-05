[← Prev: Feature Overview](feature-overview.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)

# Voice Control (local & offline)

Operate the workbench **by voice** — navigate panels, trigger actions, and dictate text into the editor or the AI question field. Everything runs **locally and offline** (Vosk speech recognition + PulseAudio capture) — no external provider, no API key, nothing leaves your computer. Built with accessibility as the priority.

Open it via the **🎤 Sprache** toolbar button.

## Setup

```bash
pip install vosk        # recording uses the system tool parec / pw-record (no PortAudio needed)
```
- **German model** into `~/.cache/vosk/`:
  - small `vosk-model-small-de-0.15` (~45 MB, fast) — enough for commands
  - large `vosk-model-de-0.21` (~1.9 GB, more accurate) — automatically preferred for dictation
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

- In **Befehle** mode, recognition is **restricted to the known command vocabulary** — so misrecognitions on commands are very rare (Vosk can only pick a known command).
- **Dictation** uses the full model; the large model gives noticeably better free text.
- Vosk is not trained on your personal voice — accuracy comes from the vocabulary restriction (commands) and model size (dictation).

## Notes & limits

- Speak clearly, keep a short pause at the end, and use a quiet room — small models are most confused by background noise.
- Abort/stop takes effect at the next recognized utterance.
- Requires `parec`/`pw-record`/`ffmpeg` (present on PipeWire/PulseAudio systems). PortAudio/`sounddevice` is intentionally **not** used because it is missing in the FreeCAD Flatpak.

---

[← Prev: Feature Overview](feature-overview.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)
