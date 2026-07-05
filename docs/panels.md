[← Prev: The User Interface](oberflaeche.md) | [Home](../README.md) | [Next: Feature Overview →](feature-overview.md)

# Panels in Detail

## ⚙ Settings Panel

The panel is scrollable — all sections are accessible even in a small dock window.

### QUICK START
Three profile buttons set template, temperature, mode and thinking to proven values with one click:
- **🎯 FreeCAD Code** – Part-Script template, temperature 0.2, expert mode
- **💬 Explanation** – Python Expert template, temperature 0.7, beginner mode
- **🧠 Thinking** – Part-Script template + Extended Thinking (Anthropic only)

### AI SOURCE
- **AI source** select (dropdown with all 19 providers)
- **🔄 Reload models** – fetch a fresh model list from the provider
- **🔌 Connection test** – checks without an AI request whether Ollama is reachable or an API key is stored; result appears as a label below the model box

### PRESET
Menu button ("── Choose preset ──"): the ★ Quick presets appear at the top level,
all other categories (🔧 Code · ⚡ FC: Performance · 🧱 FreeCAD: Create ·
🔍 FreeCAD: Analyse · 📦 FreeCAD: Extend) as submenus.

### MODEL PARAMETERS
- **Temperature** 0.0–2.0 (recommended: 0.0–0.3 for code, 0.5–0.8 for documentation)
- **Top-P · Top-K · Max Tokens · Context** — all values are saved **per model** and loaded automatically on switch

### MODE
- 🟢 **Beginner** – detailed explanations in plain language
- 🔵 **Expert** – concise, technical responses
- Selection is **automatically restored** on the next start

### COLOUR SCHEME
- 🌙 Dark / ☀ Light – switches all colours immediately, selection is saved

### API KEYS
- Enter & auto-save API key per provider
- Alternative: enter `file:/path/to/key-file` → key is read from the file at runtime

### SYSTEM PROMPT ADDITION
- Free text field for custom instructions to the AI
- **📋 button** opens a template menu with predefined prompts:
  - 🧱 FreeCAD Part-Script (forces `Part.makeBox + .cut()`, no `Part::Cut`)
  - 🤖 FreeCAD AI FC14 JSON Tools (for JSON tool-calling with FC14)
  - 🐍 Python Expert (standard)
  - 🔍 Code Analysis
  - 📐 Parametric Model
  - 🛡 Security Review
- The template can be edited directly in the field after loading
- If the text starts with **"You are"** → it replaces the base prompt entirely
- Otherwise → it is appended to the base prompt

### RETENTION
- **Max. sessions** – maximum number of stored chat sessions

### AUTO-INSERT
- When active: AI response is **automatically** inserted at the found position after stream end (equivalent to manually clicking ➕ Insert)

### THINKING (ANTHROPIC)
- **Off** (default) – normal mode
- **On** – Extended Thinking with 8,000 budget tokens; `temperature` and `top_p` are automatically omitted (API requirement)
- Only effective with Anthropic models

## 🤖 AI Panel
- **One combined field** for input and response, subdivided internally by labels only:
  - **❓ Question:** at the top – enter a question or task freely (overrides the selected preset)
  - **Code block:** below – paste code to analyse or edit (type `/snippetname` → snippet autocomplete opens)
  - **AI response:** at the bottom – response appears live-streamed; same green background as the input areas, separated only by the label
  - All three areas are **freely resizable** — drag the boundary between them with the mouse
  - Question + code block are sent to the AI together on `🤖 Ask`
- **Project context** – collapsible section (▶ 📌) at the bottom of the panel; its content is sent with every AI call as background information. Collapsed by default so the input and response fields get the full panel height
- **Search/Replace** (Ctrl+F) – directly in the panel
- **💾 Save session** – save chat history + AI response + provider as `.json`
- **📂 Load session** – restore a saved session
- **🧹 Reset history** – clears the entire chat history and display
- Chat history with automatic compacting

## 🎛 Actions Panel
All action buttons at a glance, grouped into sections:

**Search field / AI input**

| Button | Function |
|--------|----------|
| 📥 Load | Load selected code from editor into AI input field |
| 🔍 Mark | Search & highlight AI input field content in editor |
| 🗑 Clear | Empty the AI input field |

**AI Actions**

| Button | Function |
|--------|----------|
| 🤖 Ask | Query the AI (with current preset); turns into **⏹ Stop** while streaming to cancel the request |
| 🔎 Analyse | Explain entire code immediately (no selection needed) |
| 🔍 Plan | **Plan mode** – display and confirm AI response before inserting |
| ✅ Replace | Replace highlighted block with AI response |
| ➕ Insert | Append AI response after the highlighted block |
| 👁 Preview | Run AI response (or editor code) directly in FreeCAD → embedded 3D viewport opens as an editor tab (▶ Run turns into ⏹ Stop while running) |

> **Running your own editor code:** press **F5** (whole macro) or **F9** (selected
> lines only) — no button needed. Press F5 again to abort a running execution.

**File**

| Button | Function |
|--------|----------|
| 💾 Save | Save current file |
| 💾✕ Save & close | Save and close tab |
| ↺ Reload | Reload file (discards unsaved changes) |
| ↩ Backup | Load newest .bak backup into editor |

**Editor**

| Button | Function |
|--------|----------|
| ☰ Select all | Select all code |
| ✕ Delete | Delete selection |
| ✨ autopep8 / 🪄 Indent | Auto-format code |

**Library**

| Button | Function |
|--------|----------|
| 📚 Save | Save current editor content to the macro library |
| 🤖📚 AI→Lib | Save the AI response to the macro library (flagged as AI-generated) |

> Navigation (jump to line, code tree, bookmarks), Edit & Check and Cleanup live in the **🔧 Tools panel** — see below.

## 🧩 Snippets & API Panel

**📦 Snippets** and **💡 API Hints** share **one panel** with two sub-tabs (open it
via the 🧩 toolbar button, then switch between the sub-tabs).

### 📦 Snippets (sub-tab)

**Local (Offline)**
- Categories: Document · Part · Sketcher · Mesh · Draft · PartDesign
- Click snippet → preview appears
- **↪ Into editor** or **double-click** → insert at cursor position
- **📋 Copy** → to clipboard

**Custom Snippets**
- Select code in editor → **💾 Save selected code as snippet**
- Enter a name → appears under ⭐ My Snippets
- Saved permanently in FreeCAD settings

**Online (GitHub)**
- Loads real FreeCAD macros directly from the official FreeCAD GitHub repo
- Preview loaded asynchronously (no UI freeze)
- Preview cache (max. 50 entries) for fast re-display

**Quick access in AI input field**
- Type `/` → popup opens automatically
- Continue typing to filter the list live
- Enter or click → snippet is loaded into the input field

### 💡 API Hints (sub-tab)
Offline quick reference for all important FreeCAD Python commands:
- **App** · Part · Sketcher · Mesh · Draft · Placement · Selection · GUI/View
- Search field: multiple words at once (e.g. `part shape`, `mesh vector`)
- Click a command → description appears below
- **📋 Copy signature** → paste directly into editor or AI input field

## 📂 File Browser
- Freely resizable (drag the panel edge)
- **Navigation:** ⬆ folder up · 🏠 home directory · 📁 macro folder — compact icon buttons with tooltips; the path field sits on its own full-width row below (Enter jumps to the path)
- **Filter:** `.py` only / `.FCMacro` only / all files
- **Double-click:** `.py`/`.FCMacro` → open in editor · other files → copy path
- **Right-click** on a file/folder → context menu: 📂 open in editor · 📁 navigate here · 🗂 set as macro path · 📄 new file here · 📋 copy path · ★ bookmark
- **Bookmarks:** ☆ button → remember folder

## 🧰 Tools & Library Panel

**🛠 Tools** and **📚 Library** share **one panel** with two sub-tabs (open it via
the 🧰 toolbar button, then switch between the **🛠 KI-Tools** and **📚 Library**
sub-tabs).

### 🛠 KI-Tools (sub-tab)

Contains three sections as collapsible areas:

**📄 FreeCAD Document Context**
Current document state (objects, types, placement) is automatically appended to every AI prompt.
→ The AI "sees" what is currently open in FreeCAD.

**🛠 Direct Tools**
Predefined, safe FreeCAD operations — no coding required:

| Tool | Parameters |
|------|------------|
| **Create primitive** | Type (Box/Cylinder/Sphere/Cone/Torus), dimensions, position |
| **Boolean operation** | Type (Cut/Fuse/Common), base object, tool object |
| **Set placement** | Object name, X/Y/Z, rotation axis, rotation angle |
| **List objects** | — (shows all objects + TypeId) |
| **Run macro** | Free Python code as fallback |

Every operation runs inside a FreeCAD undo transaction → fully reversible.
Result buttons: **▶ Run** · **📥 Into editor** · **➕ Append**

**📋 Log**
All executions with timestamp, ✅/❌ status and output. 🗑 Clear button.

### 📚 Library (sub-tab)

See [Macro Library](makro-bibliothek.md) for details.

## 🔧 Tools Panel

**Code tree:** all `def`/`class` listed automatically → double-click jumps to definition

**Navigation**

| Function | Description |
|----------|-------------|
| Jump to line | Enter line number → Enter |
| Bookmarks | ＋ set · ↑↓ navigate · 🗑 delete |

**Edit & Check**

| Button | Function |
|--------|----------|
| → Indent / ← Unindent | Indent/unindent selection by 4 spaces |
| # Toggle | Add or remove comment character |
| ⧉ Duplicate | Duplicate selection/line |
| ✂ Delete | Delete selection/line |
| ⬆ / ⬇ Move | Move line(s) up/down |
| ABC / abc / Abc | Transform case |
| ↺ Statistics | Lines, comments, def, class, import, characters |
| ▶ Syntax check | Check Python syntax → error location with line number |

**Cleanup**

| Button | Function |
|--------|----------|
| ␣ Trailing spaces | Remove whitespace at end of lines |
| ⬜ Max 2 blank lines | Trim more than 2 consecutive blank lines |
| ¶ Trailing blank lines | Remove blank lines at end of file |
| Remove BOM | Remove UTF-8 byte-order mark from file |

## ♿ Help+Access Panel

One dock with four tabs: **🤝 Assist.** (interactive assistant) · **🔧 Helper** (dyslexia assistant + vision) · **♿ Access** (accessibility settings) · **❓ Help** (built-in documentation). The individual tabs are described below.

### ❓ Help Tab

Searchable, collapsible built-in documentation covering all panels, workflows,
shortcuts and known limitations. The search field filters sections live —
matching sections expand automatically.

## 🔧 Helper Panel (Accessibility & Vision)

A chat tab (in the ♿ Help+Access dock) with two functions:

### Dyslexia Assistant
Convert freely written text (spelling errors OK) into a clean FreeCAD description:
```
i need a box with hole to screw on the wall
→ AI corrects → "A rectangular bracket with mounting hole for wall attachment"
```
- Real-time spell checking while typing (using `pyspellchecker`)
- Diff view of corrections (red = removed, green = added)
- Result can be transferred directly into the editor

### Send Text + Image to AI (Vision)
- **📎 Attach image** – file dialog with provider-specific formats
- **📋 From clipboard** – Ctrl+V or button
- **Drag & Drop** – drag image file directly into the input field
- Thumbnail preview with image size display and ✕ button
- Warning when the selected model does not support vision
- Allowed formats are loaded automatically per provider (no hardcoding)

| Provider | Vision models | Formats |
|----------|--------------|---------|
| Ollama (Local) | llava, bakllava, moondream, minicpm-v | JPEG, PNG, WebP, GIF, BMP |
| Anthropic (Claude) | claude-3+ | JPEG, PNG, GIF, WebP |
| OpenAI (ChatGPT) | gpt-4o, gpt-4-turbo | JPEG, PNG, GIF, WebP |
| Gemini (Google) | gemini-1.5+ | JPEG, PNG, GIF, WebP, HEIC + more |
| OpenRouter (Cloud) | model-dependent | JPEG, PNG, GIF, WebP |

## ⚠ Error Panel

One single surface (no page switching): output, runtime errors and the test
sandbox share the same field. Buttons: 🧪 Test · 🔧 AI fix · 🔍 Translate ⇄
🔙 Original (in place) · 🐛 AI explains · 🗑 Clear.

See [Error Panel & Sandbox / Backup System](fehler-und-backup.md) for details.

---

## 🎤 Voice Control Panel

Operate the workbench by voice — fully local and offline (Vosk + PulseAudio),
no external provider. Navigate panels, trigger actions, and dictate text into
the editor or the AI question field. Click **🎤 Zuhören** or press **F4**; it
stops automatically at the speech pause (no key to hold). Three big mode buttons
switch between **🧭 Befehle**, **✍ Editor** and **✍ KI**.

See [Voice Control](sprachsteuerung.md) for the full command list and setup.

---

## 🤝 Assistant Panel

An interactive step-by-step assistant with two modes:

### Normal Help Mode

Answers questions about the editor and highlights the relevant buttons and panels directly.

**Usage:**
1. Click `🤝 Assist.` in the toolbar
2. Type a question in the input field, e.g.:
   - *"how do I translate an error?"*
   - *"how do I set up Ollama?"*
   - *"how do I use plan mode?"*
3. Press **❓ Ask** or Enter
4. The AI responds in numbered steps
5. The mentioned panels/buttons light up automatically in sequence (2.2 s interval)
   – closed panels open automatically

**Notes:**
- Works with the currently selected AI provider (⚙ Settings)
- For Ollama (local) a compact system prompt is used — for cloud providers the more detailed one
- **🗑 Clear history** empties the chat display

### 🔤 Technical Language Mode (Natural Language → FreeCAD Terminology)

Toggle at the top of the Assistant panel → the assistant translates
free-form descriptions into structured FreeCAD terminology.

**Why this is useful:**
Ollama produces significantly more reliable code when given structured
terminology as input instead of free-form text. Technical language mode
is the first step in the two-stage workflow:

```
[Technical language mode ON]
Input:   "Sphere 30mm radius. Cylinder 10mm radius 60mm height through the centre"
Output:
  Part::Sphere Radius=30 mm, centre at origin.
  Part::Cylinder Radius=10 mm, Height=60 mm, Placement.Base=App.Vector(0, 0, -30).
  Part::Cut: Base=sphere, Tool=cylinder.

[Technical language mode OFF]
Paste this terminology into the FC11 input field → generate code
```

The terminology can be reviewed and corrected before being passed on.

---

## ♿ Accessibility Panel

Adjustments for visual impairment, motor difficulties, and personal preferences. All settings are
saved and automatically restored on the next start.

### 👁 Visual

| Setting | Function |
|---------|----------|
| **UI font size** (slider 8–24 pt) | Adjust font size of all labels live |
| **Editor font size** (slider 8–24 pt) | Adjust font size in the code editor |
| **High contrast** | All UI elements: white on black (overrides the theme) |
| **Icons with text** | Toolbar buttons show emoji + short name, e.g. `⚙ Settings` instead of just `⚙` |

### 🖐 Motor

| Setting | Function |
|---------|----------|
| **Button size** Normal / Large / Extra large | Height of all buttons: 26 / 34 / 42 px |
| **Keyboard mode** | Alt+1 to Alt+0 open the panels; shortcut shown in tooltip |
| **Simple view** | Hides rarely used panels from the toolbar |

### 💬 Plain Language

| Setting | Function |
|---------|----------|
| **AI responds in plain language** | AI uses short sentences, avoids jargon |
| **Explain technical terms automatically** | AI explains terms it uses immediately after |
| **Keep AI responses shorter** | Compact answers without long explanations |

### ⚙ General

| Setting | Function |
|---------|----------|
| **Tooltips always visible** | Tooltip appears immediately on hover (no delay) |
| **Reduce animations** | Button highlight lasts 300 ms instead of 1,800 ms |

---

[← Prev: The User Interface](oberflaeche.md) | [Home](../README.md) | [Next: Feature Overview →](feature-overview.md)
