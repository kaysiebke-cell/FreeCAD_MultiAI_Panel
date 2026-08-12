[← Prev: Voice Control](sprachsteuerung.md) | [Home](../README.md) | [Next: Setting Up AI Providers →](setting-up-ai-providers.md)

# AI Workflow & Presets

## Standard Workflow (edit / improve code)
```
1. Select a block in the editor
2. 📥 Load  →  block appears in the AI input field
3. Choose a preset  (e.g. "Find & explain errors")
4. 🤖 Ask  →  AI response appears live
5. 🔍 Mark  →  block is highlighted in the editor
6. ✅ Replace  →  backup is created, code is replaced
```

**Stop a request:** while the AI is streaming, **🤖 Ask** turns into **⏹ Stop**.
Click it (or press Ctrl+Shift+K again) to cancel the running request — the partial
answer is kept.

## Quick Analysis (without selection)
```
🔎 Auto-Analyze  →  entire code is explained immediately
```

## Insert code after a block
```
Select block → 📥 Load → 🤖 Ask → ➕ Insert
→  AI response is appended AFTER the block (no overwriting)
```

## Auto-Insert (automatic after AI response)
```
⚙ Settings → AUTO-INSERT ✓ enable
→ After every stream end, the AI response is inserted automatically
→  (no manual click on ➕ Insert needed)
```
Disable this if you want to review the response before it is inserted.

## Plan Mode (review code before inserting)
```
🔍 Plan  activate (button in the Actions panel)
→ 🤖 Ask
→ ✅ Replace  →  a dialog opens showing the new code for review
   → ✅ Run     →  code is replaced
   → ❌ Cancel  →  nothing changes, no backup created
```
Ideal for critical sections — no accidental overwriting of important code.

## Run editor code (F5 / F9)
```
F5  →  save + run the WHOLE macro directly in FreeCAD
       (result in the FreeCAD window; only errors open the ⚠ panel)
F9  →  run ONLY the selected lines (or the current line)
       — ideal for trying things out step by step
```
**Abort:** press **F5** again (or the ⏹ button) to stop a running execution at
the next Python line. A FreeCAD C++ operation already in progress cannot be
interrupted — the abort takes effect at the next line.

## 👁 Preview (run code in FreeCAD)
```
👁 Preview  (button in the Actions panel)
→ Runs the AI response (or the editor code) directly in FreeCAD
→ The embedded 3D viewport opens as a "👁 Preview" tab in the editor
→ Buttons in the tab: ▶ Run · 🔄 Refresh · ⊡ Fit
   (▶ Run turns into ⏹ Stop while a run is in progress)
```
⚠️ The code is really executed — changes to the FreeCAD document are real.
If a runtime error occurs, the **⚠ Error panel** opens with the error, where you
can 🔍 Translate, 🐛 have the AI explain it, or 🔧 AI-fix it.

## Save & restore session
```
💾  →  file dialog  →  save as .json
        (chat history + AI response + provider + model)

📂  →  open .json  →  everything is restored
```
On the next FreeCAD start, simply load the `.json` file and continue seamlessly.

## Project folder as context
By default the AI only sees the file you have open. To give it a whole project — several
folders and files — pick a project folder:

```
🤖 AI panel → ▶ 📌 Project context → 📁 Choose …
```

What is sent is a **map, not source code**: the folder tree plus every class and function of
the Python files in it. This usually costs only a few hundred tokens no matter how large the
project is. For Ollama the frugal variant (folder tree only) is used automatically, so the
small context window of local models is not blown.

When the AI needs the actual content of a file, it asks for it itself:

```
#DATEI: core/params.py     → the file is loaded and the request continues
#SUCHE: Placement          → matches across the project are supplied
```

The file is fetched automatically and the request re-runs with that content (max. 2 rounds per
question, max. 3 files per round). The status bar shows `📂 Lade nach …` while this happens.
Because this uses plain text markers instead of a provider-specific tool API, it works with all
19 providers — including local Ollama models without tool support.

The same three operations are also available as manual buttons in the **🔧 Tools panel**
(`projekt_dateien_auflisten`, `projekt_datei_lesen`, `projekt_suchen`).

| Detail | Behaviour |
|--------|-----------|
| Checkbox "Projektübersicht … mitschicken" | Turns the map off without losing the folder |
| ✕ button | Clears the project folder |
| Skipped | `__pycache__`, `.git`, `node_modules`, `venv`, `build`, `dist`, files > 200 KB, non-text files |
| Limits | 400 files, 12,000 characters of map |
| Access | Read-only, and never outside the chosen folder |

## Using the chat history
The chat history is kept between questions. Follow-up questions build on previous answers.
After 5,000 characters the oldest part is automatically compressed (summarised).

## System prompt templates
```
⚙ Settings → SYSTEM PROMPT ADDITION → click 📋 button
→ Select a template → text appears in the field
→ Optional: edit directly in the field
→ Saved automatically
```

| Template | Use case |
|----------|----------|
| 🧱 FreeCAD Part-Script | Forces `Part.makeBox + .cut()`, prevents error-prone `Part::Cut` feature approach |
| 🤖 FreeCAD AI FC14 JSON | For JSON tool-calling with the FC14 preset |
| 🐍 Python Expert | Standard prompt for general coding tasks |
| 🔍 Code Analysis | Structured error analysis with line numbers |
| 📐 Parametric Model | All dimensions as constants, complete FreeCAD script |
| 🛡 Security Review | Critical/Medium/Low classification of security issues |

**Tip:** If your own text starts with "You are …" → it replaces the base prompt entirely. Otherwise it is appended as an addition.

---

# AI Presets

Over 40 predefined task templates in 6 categories, selected via the preset
**menu button** in the ⚙ Settings panel — the ★ Quick presets appear at the
top level, all other categories as submenus:

## ★ Quick
- What does this code do?
- Find & explain errors
- Improve code
- Summary
- Explain simply

## 🔧 Code
- Refactoring · Add comments · Performance optimisation · Bug hunt
- SOLID refactoring · Security review · Threading · Production-ready

## ⚡ FreeCAD: Performance
- Performance analysis · Check transactions · Optimise loops

## 🧱 FreeCAD: Create
- Create macro · Parametric model · PartDesign script · Add GUI dialog
- **FC11** – Macro from description (Natural language → Part code)
- **FC12** – PartDesign from description (Natural language → Body/Sketch/Pad)
- **FC13** – Build step by step (extend a model incrementally)
- **FC14** – Object commands (local) — simple Part commands only, ideal for Ollama and JSON tool-calling

→ Details on FC11/FC12/FC13: [Macro from Description](makro-generator.md)  
→ Ollama experiences & model comparison: [Ollama Field Report](OLLAMA_ERFAHRUNGEN.md)

**Tip for Ollama + FC11:** First open the 🤝 Assistant panel and activate **🔤 Technical language mode**,
translate the natural description into structured FreeCAD terminology,
then paste that terminology into FC11. Ollama produces significantly more reliable code
from structured input than from free-form text.

## 🔍 FreeCAD: Analyse
- Error hunting · Selection macro · Mesh processing

## 📦 FreeCAD: Extend
- Workbench class · STEP/IGES export · Batch processing · Backup extension

---

[← Prev: Voice Control](sprachsteuerung.md) | [Home](../README.md) | [Next: Setting Up AI Providers →](setting-up-ai-providers.md)
