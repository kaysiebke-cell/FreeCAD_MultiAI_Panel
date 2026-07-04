[← Back: Macro Library](makro-bibliothek.md) | [Back to README](../README.md) | Next: [Ollama – Field Report →](OLLAMA_ERFAHRUNGEN.md)

# Error Panel & Sandbox

The **⚠ Error** panel (bottom edge) is **one single surface** — output, runtime
errors and the test sandbox all share the same field. There is no more page
switching. The error sits in the output field; every action is a button above it:

| Button | Function |
|--------|----------|
| 🧪 Test | Syntax check + trial run of the loaded (AI) code — no real document changes |
| 🔧 AI fix | Send error + code to the AI and get corrected code back (max. 3 attempts) |
| 🔍 Translate | Translate the error message into German **1:1, in place** — the text is *replaced*, not duplicated. The button then becomes 🔙 **Original** and switches back (one button, two states — like a browser) |
| 🐛 AI explains | Detailed AI explanation of the error in German (answer streams into the 🤖 AI panel) |
| 🗑 Clear | Reset the field and its state |

```
Output / Error:

  AttributeError: 'NoneType' object has no attribute 'Shape'

→ 🔍 Translate  →  same field now shows:

  ❌ Object is None
  »Shape« was called on None.
  Possible causes: function returns None instead of an object …

→ 🔙 Original   →  back to the English message
```

Recognised error types when translating: `AttributeError` · `TypeError` ·
`NameError` · `ImportError` · `No active document` · Shape errors · Constraint errors.

**Good to know:** 🐛 AI explains and 🔧 AI fix always use the **real English
error** — even while the German translation is on screen.

Double-click a `»line N«` reference in the field to jump to that line in the editor.

**Where the errors come from:**
- **F5 / F9** runs and the **👁 Preview** place runtime errors here automatically and open the panel.
- AI-generated code lands here for a 🧪 trial run before you replace your code.

> A separate **error-translator tab** lives in the left dock (Snippets area):
> paste any English error and press **Ctrl+Enter** for a quick standalone translation.

---

# Backup System

- Before every **✅ Replace**, a `.bak` file is created automatically
- Backups are stored in a dedicated **`__backups__/`** subfolder next to the original file
- Maximum **3 backups** per file (oldest are deleted automatically)
- **↩ Backup** in the Actions panel loads the newest backup into the editor
- On close with unsaved changes: Save / Discard / Cancel

```
Macro folder/
├── my_script.py
└── __backups__/
    ├── my_script.py.20260615_201500.bak
    ├── my_script.py.20260615_202100.bak
    └── my_script.py.20260615_203000.bak
```

---

[← Back: Macro Library](makro-bibliothek.md) | [Back to README](../README.md) | Next: [Ollama – Field Report →](OLLAMA_ERFAHRUNGEN.md)
