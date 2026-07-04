[← Prev: Panels in Detail](panels.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)

# Feature Overview

This file summarizes the main features of the FreeCAD MultiAI Panel: editor capabilities, AI integration, and UI highlights.

## Editor

- Multiple files open simultaneously as tabs with drag & drop
- Python syntax highlighting (adapts to light/dark theme)
- Line numbers, indent guides, cursor position
- Jedi-based autocomplete (optional)
- Search & replace
- Run code in FreeCAD: F5 runs whole macro (saves first), F9 runs selection/current line
- Abort a run: press F5 again (stops at the next Python line)
- Unlimited undo/redo
- Automatic backups before AI replacements (max. 3 per file)
- Optional autopep8 formatting

## AI Integration

- Support for many providers (local and cloud)
- Presets and quick-start profiles for common workflows
- Streaming responses and abortable AI requests
- Two modes: Beginner (detailed) and Expert (concise)
- Generate macros from natural language (FC11–FC13) and FC14 tool-calling
- Skills (domain snippets) appended to prompts when relevant
- FreeCAD document state can be included in prompts
- AGENTS.md support and system prompt templates

## User Interface

- 9 freely arrangeable dock panels
- Light/dark mode and per-panel toggles
- Interactive assistant and built-in help panel
- Accessibility options: font size, contrast, keyboard mode, simplified view, tooltip delay, reduced animations

For detailed workflows and presets see `docs/ki-workflow.md`.

---

[← Prev: Panels in Detail](panels.md) | [Home](../README.md) | [Next: AI Workflow & Presets →](ki-workflow.md)
