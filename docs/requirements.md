[← Prev: Quick Start](quick-start.md) | [Home](../README.md) | [Next: First Start & Welcome →](erststart.md)

# Requirements & Installation

## Requirements

- FreeCAD 0.21 or newer
- Python 3.10+

## Required package

Install the runtime dependency used for AI connections:

```bash
pip install requests
```

Needed for all AI connections. Without `requests` the editor starts but all AI features are disabled.

## Optional packages

```bash
pip install jedi            # Python autocomplete in the editor
pip install autopep8        # automatic PEP-8 formatting (enables the autopep8 button)
pip install pyspellchecker  # spell checking in the helper panel (pure Python, Flatpak-compatible)
```

Install all at once:

```bash
pip install requests jedi autopep8 pyspellchecker
```

### Flatpak users

Packages must be installed via the embedded Python inside the Flatpak:

```bash
flatpak run --command=python3 org.freecad.FreeCAD -m pip install pyspellchecker
```

If the workbench does not load in Flatpak, grant FreeCAD access to the home folder:

```bash
flatpak override --user --filesystem=home org.freecad.FreeCAD
```

### FreeCAD AppImage / Restart

After installing packages, restart FreeCAD. For AppImages the embedded Python may need to be targeted (e.g. extract the AppImage and use the included Python).

### Installing the plugin

1. Clone this repository or download and extract the ZIP
2. Rename the folder to `FreeCAD_MultiAI_Panel` (no spaces — important!)

#### Linux – AppImage

```bash
mkdir -p ~/.local/share/FreeCAD/v1-1/Mod
ln -s /path/to/FreeCAD_MultiAI_Panel ~/.local/share/FreeCAD/v1-1/Mod/FreeCAD_MultiAI_Panel
```

#### Linux – Flatpak

```bash
mkdir -p ~/.var/app/org.freecad.FreeCAD/data/FreeCAD/v1-1/Mod
ln -s /path/to/FreeCAD_MultiAI_Panel ~/.var/app/org.freecad.FreeCAD/data/FreeCAD/v1-1/Mod/FreeCAD_MultiAI_Panel
```

#### Windows

Place the folder in:

```
%APPDATA%\FreeCAD\Mod\FreeCAD_MultiAI_Panel\
```

#### macOS

Place the folder in:

```
~/Library/Preferences/FreeCAD/Mod/FreeCAD_MultiAI_Panel/
```

> Note for Linux: FreeCAD 1.x stores user data under `v1-1/` — older guides without this subfolder will not work.

---

[← Prev: Quick Start](quick-start.md) | [Home](../README.md) | [Next: First Start & Welcome →](erststart.md)
