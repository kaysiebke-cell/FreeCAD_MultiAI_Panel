[← Prev: Ollama – Field Report](OLLAMA_ERFAHRUNGEN.md) | [Home](../README.md) | [Next: Known Limitations →](known-limitations.md)

# Project Structure

Top-level layout of the repository (important files and folders):

```
FreeCAD_MultiAI_Panel/

├── main.py              # Entry point (FreeCAD macro / sidebar)
├── InitGui.py           # FreeCAD GUI integration (toolbar button)
├── package.xml          # FreeCAD addon metadata
├── README.md            # Short entry README

├── core/                # Core helpers: params, theme, highlighter, etc.
├── editor/              # Editor implementation (UI builders, controllers, subsystems)
├── ui/                  # Dialogs and UI helpers (welcome, accessibility, error translator)
├── data/                # Snippets, presets, API hints, skills
├── assets/              # Icons, demo GIF
├── docs/                # Documentation (this folder)
└── tests/               # Tests
```

For a detailed view of files and responsibilities, consult the original full README content moved to `docs/full_readme.md`.

---

[← Prev: Ollama – Field Report](OLLAMA_ERFAHRUNGEN.md) | [Home](../README.md) | [Next: Known Limitations →](known-limitations.md)
