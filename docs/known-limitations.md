[← Prev: Project Structure](project-structure.md) | [Home](../README.md)

# Known Limitations

| Problem | Cause | Solution |
|---------|-------|----------|
| Emojis displayed as outlines in Flatpak | Flatpak sandbox blocks system emoji fonts | Use native package or AppImage |
| FC12/FC13 disabled for Ollama | Too complex for local models | Use Claude (Anthropic) or GPT-4o |
| API keys stored unencrypted | FreeCAD settings have no encryption | Do not use production keys |
| Large files (>2,000 lines) | AI context window is limited | Load only relevant sections into the input field |
| Ollama not found | Service is not running | Run `ollama serve` in the terminal |
| Ollama produces poor FreeCAD code | General model without code focus | Install `ollama pull qwen2.5-coder:7b` |
| Aborting a run only stops between Python lines | A running FreeCAD C++ operation cannot be interrupted | Wait for the current operation; the abort takes effect at the next line |
| Stopping an AI request waits for the next chunk | The stream breaks at the next received line, not mid-socket | A fully stalled provider still ends via the 120 s timeout |

If you want, I can split or expand any of these into separate troubleshooting pages.

---

[← Prev: Project Structure](project-structure.md) | [Home](../README.md)
