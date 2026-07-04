# Quick Start

A short quick-start to get the workbench running.

1. Install required package:

```bash
pip install requests
```

2. Place the folder in your FreeCAD Mod directory, named exactly `FreeCAD_MultiAI_Panel` (no spaces).

3. Restart FreeCAD. The workbench "FreeCAD MultiAI Panel" will appear in the workbench menu.

4. Configure an AI provider in the Welcome dialog or skip and configure later from the settings.

## Platform notes

- Flatpak: use the embedded Python to install optional packages (see `docs/requirements.md`).
- AppImage: restart FreeCAD after installing packages; you may have to target the embedded Python inside the AppImage.

## Workflow note

The integrated AI workflow (see `docs/ki-workflow.md`) demonstrates how AI support fits into development — from presets to streaming and tool-based FC14 calls.