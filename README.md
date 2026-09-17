# VELO 2.0 - Local AI Assistant with iOS-Style Notch UI

A local-first AI assistant for Windows featuring a sleek, frosted-glass top-center notch UI, voice/text control, local wake-word detection, and a strict Human-in-the-Loop (HITL) permission engine.

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   velo_ui       │ ◄─────────────────► │    velo_core     │
│  (Electron +    │   Real-time events  │   (FastAPI)      │
│   React + TS)   │                     │                  │
└─────────────────┘                     └────────┬─────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
             ┌─────────────┐            ┌─────────────────┐          ┌──────────────┐
             │   Ollama    │            │  faster-whisper │          │  Playwright  │
             │  (Local LLM)│            │   (Local STT)   │          │  (Browser    │
             │             │            │                 │          │   Automation)│
             └─────────────┘            └─────────────────┘          └──────────────┘
                    │                            │                            │
                    ▼                            ▼                            ▼
             ┌────────────────────────────────────────────────────────────────────────┐
             │                         Your Laptop (Windows)                          │
             │  - Chrome profile with active sessions (Google, GitHub, etc.)          │
             │  - Microphone for wake word "Hi Velo"                                  │
             │  - Shell access (with HITL permission)                                 │
             └────────────────────────────────────────────────────────────────────────┘
```

## Features

- **iOS-Style Notch UI**: Floating, frameless, transparent window at top-center of screen
- **Wake Word Detection**: "Hi Velo" using Porcupine (fully local)
- **Speech-to-Text**: faster-whisper (local, no cloud)
- **Local LLM**: Ollama with function calling (llama3.1:8b, qwen2.5:7b, etc.)
- **Browser Automation**: Playwright CDP to your existing Chrome profile
- **HITL Permissions**: Explicit Allow/Deny for mutating actions
- **Tools**: Web search, shell commands, clipboard, browser control

## Prerequisites

1. **Ollama**: `winget install Ollama.Ollama` → `ollama pull llama3.1:8b`
2. **Chrome with CDP**: Create shortcut with:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDevProfile"
   ```
3. **Porcupine Access Key**: Free at https://picovoice.ai/ (add to `velo_core/.env`)
4. **Python 3.11+**, **Node 20+**, **Git**

## Quick Start

```powershell
# Terminal 1: Start all services
cd D:\VELO2
.\scripts\dev.ps1

# Or manually:
# Terminal 1: ollama serve
# Terminal 2: Chrome with CDP (see shortcut above)
# Terminal 3: cd velo_core && .\.venv\Scripts\python.exe -m velo_core.main
# Terminal 4: cd velo_ui && npm run dev
```

## Configuration

### velo_core/.env
```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
WHISPER_MODEL=base
PORCUPINE_ACCESS_KEY=your_key_here
CHROME_DEBUG_PORT=9222
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8000
```

### velo_ui/.env
```env
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
D:\VELO2\
├── velo_ui/                 # Electron + React + TypeScript (Notch UI)
│   ├── electron/            # Main process, preload, window config
│   ├── src/
│   │   ├── components/      # Notch, Waveform, Transcription, PermissionPrompt
│   │   ├── context/         # NotchContext (state management)
│   │   ├── hooks/           # useWebSocket, useNotchController
│   │   └── types/           # TypeScript types
│   └── package.json
│
├── velo_core/               # FastAPI Backend
│   ├── velo_core/
│   │   ├── main.py          # FastAPI entry + WebSocket
│   │   ├── config.py        # Pydantic Settings
│   │   ├── audio.py         # Wake word + STT daemon
│   │   ├── agent.py         # Ollama orchestration + tool execution
│   │   ├── security.py      # HITL PermissionGate
│   │   ├── tools/           # Tool implementations
│   │   │   ├── base.py      # @tool decorator + registry
│   │   │   ├── browser.py   # Playwright CDP tools
│   │   │   ├── shell.py     # Shell commands + clipboard
│   │   │   └── search.py    # DuckDuckGo HTML scrape
│   │   ├── services/
│   │   │   ├── ollama.py    # Ollama client with tools
│   │   │   └── browser_pool.py # Persistent Chrome connection
│   │   └── websocket/       # Connection manager + handlers
│   └── requirements.txt
│
├── scripts/
│   └── dev.ps1              # Development launcher
└── README.md
```

## Available Tools

| Tool | Description | Permission |
|------|-------------|------------|
| `open_url` | Open URL in Chrome | ❌ |
| `click_element` | Click CSS selector | ❌ |
| `type_text` | Type into input | ❌ |
| `extract_text` | Get page/element text | ❌ |
| `search_web` | DuckDuckGo search | ❌ |
| `run_shell` | Run allowed command | ✅ (high) |
| `get_clipboard` | Read clipboard | ❌ |
| `set_clipboard` | Write clipboard | ✅ (low) |

## HITL Flow

```
User: "Hi Velo, open github.com"
         │
         ▼
Wake word detected → Notch: LISTENING (waveform animation)
         │
         ▼
STT transcribes → "open github.com"
         │
         ▼
Ollama: tool_call(open_url, {url: "https://github.com"})
         │
         ▼
Tool requires_permission=false → Execute immediately
         │
         ▼
Notch: EXPANDED → ToolStatusCard (success) → IDLE
```

For `run_shell` or `set_clipboard`:
```
         ▼
PermissionGate intercepts → Notch: PERMISSION (Allow/Deny card)
         │
         ├─ ALLOW → Execute → ToolStatusCard → IDLE
         └─ DENY  → Cancel → "Permission denied" → IDLE
```

## Development

```powershell
# Backend
cd velo_core
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe -m velo_core.main

# Frontend
cd velo_ui
npm install
npm run dev          # Vite dev server
npm run electron:dev # Electron + Vite
npm run forge:package # Package as portable ZIP
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Notch not appearing | Check Electron DevTools (Ctrl+Shift+I), verify WebSocket connection |
| Wake word not working | Verify Porcupine key in `.env`, check microphone permissions |
| STT not transcribing | Check `faster-whisper` model downloaded, verify audio input |
| Chrome CDP connection failed | Ensure Chrome started with `--remote-debugging-port=9222` |
| Ollama tool calling fails | Try `qwen2.5:7b` or `nemotron3:8b` models |
| Permission prompt not showing | Check WebSocket `permission_request` event in browser DevTools |

## License

MIT