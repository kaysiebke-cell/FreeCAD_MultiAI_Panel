[← Prev: Ollama – Field Report](OLLAMA_ERFAHRUNGEN.md) | [Home](../README.md) | [Next: Known Limitations →](known-limitations.md)

# Project Structure

Top-level layout of the repository (important files and folders):

```
FreeCAD_MultiAI_Panel/

├── main.py              # Entry point (FreeCAD macro / sidebar)
├── InitGui.py           # FreeCAD GUI integration (toolbar button)
├── Icon.svg             # Workbench icon
├── package.xml          # FreeCAD addon metadata (Addon Manager)
├── LICENSE              # MIT license
├── README.md            # Short entry README

├── core/                # Core helpers: params, theme, highlighter, etc.
├── editor/              # Editor implementation (UI builders, controllers, subsystems)
│   ├── ki/              # AI modules (streaming, prompts, self-correction, tool-calling)
│   ├── fehler/          # Error panel + sandbox
│   └── sprache/         # 🎤 Voice control (Vosk, offline) — see docs/sprachsteuerung.md
├── ui/                  # Dialogs and UI helpers (welcome, accessibility, error translator)
├── data/                # Snippets, presets, API hints, skills
├── assets/              # Icons, demo GIF
├── docs/                # Documentation (this folder)
└── tests/               # Tests
```

For a per-file view of responsibilities, see the other pages in this documentation set (Panels, Voice Control, AI Workflow, …).

---

[← Prev: Ollama – Field Report](OLLAMA_ERFAHRUNGEN.md) | [Home](../README.md) | [Next: Known Limitations →](known-limitations.md)
