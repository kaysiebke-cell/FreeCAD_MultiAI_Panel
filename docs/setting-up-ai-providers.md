# Setting Up AI Providers

This document lists supported providers and shows how to set up local (Ollama) and cloud providers.

## Supported providers (selection)

- Ollama (local)
- Anthropic (Claude)
- OpenAI (ChatGPT)
- GitHub Copilot
- DeepSeek
- Google Gemini
- Groq
- Mistral
- Together AI
- Hugging Face
- xAI (Grok)
- Fireworks AI
- OpenRouter
- Moonshot
- Qwen (Alibaba)
- Cohere
- SambaNova
- MiniMax
- Llama API

For full provider/model details see the original README or the in‑app provider list.

## Ollama (local, free)

Ollama runs locally and requires no API key. Recommended for offline/local usage.

Steps:

```bash
# 1. Install Ollama: https://ollama.ai
# 2. Download recommended model for FreeCAD code
ollama pull qwen2.5-coder:7b   # recommended for FC11 macros

# Alternative general models
ollama pull codellama
ollama pull llama3

# 3. Start the Ollama service (runs on http://localhost:11434)
ollama serve
```

In the editor: Settings → Source: `Ollama (Local)` → no API key needed → Reload models

Tip: The editor detects installed code models and shows a hint if `qwen2.5-coder` is missing.

## Cloud providers (Anthropic / OpenAI / others)

For cloud providers enter an API key in the welcome dialog or the settings (the editor saves it in FreeCAD settings).

In the editor: Settings → select provider → enter API key → press Tab (saved automatically)

### OpenRouter

Set the environment variable before starting FreeCAD:

```bash
export OPENROUTER_API_KEY=sk-or-...
```

## Security note

API keys are stored unencrypted in FreeCAD settings — do not use production keys with full account permissions. Consider using restricted keys or file-based keys where supported.