# VELO 2.0 - Project Plan & Status

## Overview
Local AI Assistant for Windows with iOS-style Dynamic Island notch UI, voice/text control, local wake-word detection, hybrid backend, and Human-in-the-Loop (HITL) permission engine.

**Tech Stack:**
- **Frontend:** Electron + React + TypeScript + Tailwind CSS + Motion (Framer Motion)
- **Backend:** Python FastAPI + WebSocket
- **LLM:** Ollama (local) - llama3.1:8b / qwen2.5:7b / nemotron3:8b
- **STT:** faster-whisper (local, CPU)
- **Wake Word:** Porcupine (Picovoice) / openWakeWord
- **Browser Automation:** Playwright + CDP to existing Chrome profile
- **OS Control:** Python subprocess (allowlisted commands)

---

## Project Structure
```
D:\VELO2\
├── velo_ui/                    # Electron + React (Notch UI)
│   ├── electron/
│   │   ├── main.ts             # Frameless, transparent, always-on-top window
│   │   ├── preload.ts          # Secure IPC bridge (contextBridge)
│   │   └── util.ts
│   ├── src/
│   │   ├── components/
│   │   │   ├── Notch.tsx       # Main notch component (4 states)
│   │   │   ├── AuroraGlow.tsx  # Animated glow from windows_island
│   │   │   ├── Waveform.tsx    # Audio visualization bars
│   │   │   ├── TranscriptionFeed.tsx
│   │   │   ├── ToolStatusCard.tsx
│   │   │   ├── PermissionPrompt.tsx
│   │   │   ├── NotificationCard.tsx  # iOS 27 style notifications
│   │   │   ├── ActivationPop.tsx     # Pink pop-out for "Hi Velo"
│   │   │   └── index.ts
│   │   ├── context/NotchContext.tsx  # State machine + notification queue
│   │   ├── hooks/useWebSocket.ts     # WS client with auto-reconnect
│   │   ├── types/notch.ts            # TypeScript types
│   │   ├── App.tsx, main.tsx, index.css
│   ├── package.json, tsconfig.json, vite.config.ts, tailwind.config.ts
│
├── velo_core/                  # FastAPI Backend
│   ├── velo_core/
│   │   ├── main.py             # FastAPI + WebSocket /ws + lifespan
│   │   ├── config.py           # Pydantic Settings (.env)
│   │   ├── audio.py            # WakeWordDetector + STTEngine + AudioDaemon
│   │   ├── agent.py            # Ollama orchestration + tool execution
│   │   ├── security.py         # PermissionGate (DI pattern, no circular imports)
│   │   ├── tools/
│   │   │   ├── base.py         # @tool decorator + TOOL_REGISTRY
│   │   │   ├── browser.py      # Playwright CDP: open_url, click, type, extract
│   │   │   ├── shell.py        # run_shell (allowlisted), get/set_clipboard
│   │   │   └── search.py       # DuckDuckGo HTML scrape
│   │   ├── services/
│   │   │   ├── ollama.py       # AsyncOllamaClient with function calling
│   │   │   └── browser_pool.py # Persistent Chrome CDP connection
│   │   ├── models/schemas.py   # Pydantic models for WS messages
│   │   └── websocket/
│   │       ├── manager.py      # ConnectionManager (broadcast, personal)
│   │       └── handlers.py     # MessageHandler + process_user_input
│   ├── requirements.txt, .env
│
├── scripts/dev.ps1             # Development launcher (starts all services)
├── plan.md                     # This file
├── README.md
└── .gitignore
```

---

## WebSocket Protocol

### Client → Server
```json
{"type": "audio_chunk", "data": "base64_pcm16"}
{"type": "wake_word_detected"}
{"type": "permission_response", "request_id": "uuid", "allowed": true}
```

### Server → Client
```json
{"type": "notch_state", "state": "idle|listening|expanded|permission|notification|activation"}
{"type": "transcription", "text": "...", "final": false}
{"type": "tool_call", "id": "uuid", "tool": "open_url", "args": {...}}
{"type": "permission_request", "id": "uuid", "tool": "...", "args": {...}, "risk": "high", "description": "..."}
{"type": "tool_result", "request_id": "uuid", "success": true, "output": "..."}
{"type": "notification", "id": "uuid", "summary": "...", "sentiment": "ambient|urgent|media"}
{"type": "activation", "phrase": "Hi Velo"}
{"type": "error", "message": "..."}
```

---

## Notch States & Visual Design

| State | Width | Height | Color/Shadow | Content |
|-------|-------|--------|--------------|---------|
| **idle** | 140 | 35 | None | Capsule with Gemini-style logo (purple-pink gradient) |
| **activation** | 420 | 80 | Pink (`#FF0080`) | "Hi Velo" + "Activating VELO..." + pulsing mic |
| **listening** | 420 | 140 | Blue (`#2979FF`) | "Listening..." + waveform bars |
| **expanded** | 420 | 140 | Green (`#1DB954`) | Transcription feed + tool status |
| **permission** | 420 | 160 | Red (`#FF1744`) | Allow/Deny card with args preview |
| **notification** | 420 | 100 | Varies by sentiment | iOS 27 style card (icon + summary) |

**Notification Sentiments:**
- `ambient` (blue) - Bell icon
- `urgent` (red) - AlertTriangle icon
- `media` (green) - Music icon

---

## Available Tools (Registered in TOOL_REGISTRY)

| Tool | Description | Permission | Risk |
|------|-------------|------------|------|
| `open_url` | Open URL in Chrome | No | - |
| `click_element` | Click CSS selector | No | - |
| `type_text` | Type into input | No | - |
| `extract_text` | Get page/element text | No | - |
| `navigate_back` | Browser back | No | - |
| `navigate_forward` | Browser forward | No | - |
| `search_web` | DuckDuckGo search | No | - |
| `run_shell` | Allowlisted commands (notepad, calc, explorer, cmd, powershell, dir, echo, copy, move, del, mkdir, rmdir) | **Yes** | High |
| `get_clipboard` | Read clipboard | No | - |
| `set_clipboard` | Write clipboard | **Yes** | Low |

---

## HITL Permission Flow
```
User says "Hi Velo, run notepad"
       │
       ▼
Wake word detected → Notch: ACTIVATION (pink pop-out, 1.5s)
       │
       ▼
Notch: LISTENING (blue waveform)
       │
       ▼
STT transcribes → "run notepad"
       │
       ▼
Ollama: tool_call(run_shell, {command: "notepad"})
       │
       ▼
PermissionGate intercepts (requires_permission=true)
       │
       ▼
Notch: PERMISSION (red card: "Run shell command: notepad.exe")
       │
       ├─ ALLOW → Execute → Notch: TOOL_STATUS (success) → EXPANDED → IDLE
       └─ DENY  → Cancel → Notch: "Permission denied" → IDLE
```

---

## Configuration Files

### velo_core/.env
```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
WHISPER_MODEL=base
PORCUPINE_ACCESS_KEY=          # Get free from picovoice.ai
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

---

## Prerequisites (User Must Install)

1. **Ollama:** `winget install Ollama.Ollama` → `ollama pull llama3.1:8b`
2. **Chrome with CDP:** Create shortcut:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDevProfile"
   ```
3. **Porcupine Access Key:** Free at https://picovoice.ai/ (add to velo_core/.env)
4. **Python 3.11+**, **Node 20+**, **Git**

---

## Development Commands

```powershell
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd D:\VELO2\velo_core
.\.venv\Scripts\python.exe -m velo_core.main

# Terminal 3: Frontend
cd D:\VELO2\velo_ui
npm run electron:dev

# Or use launcher (starts all):
cd D:\VELO2
.\scripts\dev.ps1
```

---

## Phase Status

### ✅ Phase 1: Foundation (COMPLETED)
- [x] Project structure created
- [x] velo_ui: Electron + Vite + React + TS + Tailwind
- [x] velo_core: FastAPI + WebSocket + Ollama client
- [x] Frameless transparent window (top-center, click-through)
- [x] Notch component with 6 states (idle, activation, listening, expanded, permission, notification)
- [x] WebSocket bridge with auto-reconnect
- [x] Tool registry with 14 tools
- [x] HITL PermissionGate (DI pattern)
- [x] Audio daemon (Porcupine + openWakeWord fallback + faster-whisper)
- [x] Notification system (ambient/urgent/media)
- [x] Pink activation pop-out for "Hi Velo"
- [x] Gemini-style logo in idle state
- [x] All TypeScript compiles clean ✅
- [x] Backend starts and health check passes ✅

### ✅ Phase 1 Bug Fixes (COMPLETED)
- [x] Fixed WSMessage discriminated union (schemas.py) — model_validate_json now works
- [x] Fixed main.py — MessageHandler properly instantiated inside lifespan
- [x] Fixed audio.py — TranscriptionMessage broadcast (was wrongly using NotchStateMessage)
- [x] Fixed all tool modules auto-registering in TOOL_REGISTRY (14 tools total)
- [x] Fixed circular imports in __init__.py files
- [x] Fixed websocket handlers.py — removed deleted websocket_endpoint reference
- [x] Fixed App.tsx — hooks now inside NotchProvider, added text-input overlay
- [x] Fixed useWebSocket.ts — permission responses properly sent over WebSocket
- [x] Added UserInputMessage for text-mode testing (no mic needed)
- [x] Added /input HTTP endpoint for testing without wake word
- [x] Settings: extra="ignore" to handle unknown .env keys
- [x] Playwright browsers installed to D:\playwright-browsers

### ✅ Phase 2: Audio Pipeline (COMPLETED)
- [x] openWakeWord fallback (no Porcupine key needed)
- [x] Improved VAD tuning (RMS threshold, silence detection)
- [x] Text-input mode via Ctrl+Space (Electron UI)
- [x] Text-input via POST /input (HTTP endpoint)
- [x] Whisper base model loaded on startup (~74MB, cached)
- [x] Multi-turn conversation history (last 20 turns)
- [x] Audio daemon properly sends TranscriptionMessage to UI
- [ ] Test with real microphone (user action required)
- [ ] Porcupine wake word (requires free key from picovoice.ai)
- [ ] openWakeWord install: pip install openwakeword (if no Porcupine key)

### ✅ Phase 3: Orchestrator & Tools (COMPLETED)
- [x] 14 tools registered: open_url, click_element, type_text, extract_text, navigate_back, navigate_forward, run_shell, get_clipboard, set_clipboard, search_web, open_antigravity_and_prompt, google_search, send_gmail, send_teams_message
- [x] Playwright CDP with fallback to local Chromium
- [x] Shell commands with allowlist + HITL permission
- [x] DuckDuckGo search (no API key)
- [x] Google Search via browser CDP
- [x] open_antigravity_and_prompt (Playwright)
- [x] Gmail OAuth2 tool (requires credentials.json)
- [x] Microsoft Teams tool via Graph API (requires TEAMS_CLIENT_ID)
- [x] Multi-turn conversation context sent to Ollama
- [x] Follow-up response after tool execution
- [ ] Test Ollama function calling (requires: ollama serve + ollama pull llama3.1:8b)
- [ ] Test Gmail (requires credentials.json from Google Cloud Console)
- [ ] Test Teams (requires Azure AD app registration)

### 🔄 Phase 4: Polish & Edge Cases (PENDING)
- [ ] Spring animation tuning (stiffness/damping)
- [ ] WebSocket reconnection resilience
- [ ] Error handling & user-facing error messages
- [ ] Audio input device selection UI
- [ ] Settings/preferences persistence
- [ ] Auto-hide timeout configuration
- [ ] Log rotation & debugging tools

### 🔄 Phase 5: Packaging & Distribution (PENDING)
- [ ] Electron Forge / electron-builder configuration
- [ ] Portable ZIP build for Windows
- [ ] Installer (NSIS) optional
- [ ] Auto-update mechanism
- [ ] Code signing (optional)
- [ ] Documentation & README finalization

---

## Known Issues / TODOs

1. **Porcupine Access Key** - Not set (wake word disabled). Add to `velo_core/.env`
2. **Ollama** - Must be running locally with model pulled
3. **Chrome CDP** - Must start Chrome with `--remote-debugging-port=9222`
4. **faster-whisper** - Downloads model on first run (~150MB for base)
5. **Windows Symlinks** - HuggingFace cache warning (enable Developer Mode or run as admin)
6. **Electron DevTools** - Opens automatically in dev mode (can disable)

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Electron over Tauri | Better Windows transparency/frameless support, mature CDP |
| React Context + Hooks | Lightweight, no extra deps, fits simple state needs |
| WebSocket (native) | Low latency, bidirectional, no Socket.IO overhead |
| Porcupine for wake word | Lightweight, accurate, free tier (3 keywords) |
| faster-whisper (base) | Good accuracy/speed balance, local CPU |
| Ollama for LLM | Fully local, OpenAI-compatible, function calling support |
| Playwright CDP | Reuses existing Chrome sessions (no re-login) |
| Pydantic Settings | Type-safe config with .env support |
| DI for PermissionGate | Avoids circular imports, testable |

---

## Testing Checklist (for next session)

### Backend
- [ ] `ollama serve` running
- [ ] Model available: `ollama list` shows llama3.1:8b
- [ ] Chrome CDP accessible at `http://localhost:9222/json/version`
- [ ] Backend starts without errors: `python -m velo_core.main`
- [ ] WebSocket connects: `ws://localhost:8000/ws`

### Frontend
- [ ] `npm run dev` serves on `http://localhost:5173`
- [ ] `npm run electron:dev` opens notch window
- [ ] Notch appears top-center, click-through when idle
- [ ] Hover enables interaction, mouse leave re-enables click-through
- [ ] TypeScript compiles: `npx tsc --noEmit`
- [ ] Build works: `npx vite build`

### Integration
- [ ] Wake word "Hi Velo" triggers activation pop-out
- [ ] Transcription appears in expanded state
- [ ] Tool execution shows status card
- [ ] Permission prompt appears for run_shell/set_clipboard
- [ ] Notifications (ambient/urgent/media) display correctly
- [ ] Auto-dismiss after 5s for notifications

---

## Next Session Starting Point

1. Run `.\scripts\dev.ps1` to start all services
2. Open Chrome with CDP if not already running
3. Test wake word → transcription → tool execution flow
4. Address any audio device issues
5. Begin Phase 2 tasks

---

## References

- Original windows_island repo: https://github.com/dhamalavishkar/windows_island.git
- Porcupine docs: https://picovoice.ai/docs/porcupine/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Ollama function calling: https://github.com/ollama/ollama/blob/main/docs/api.md#function-calling
- Playwright CDP: https://playwright.dev/docs/api/class-browser#browser-connect-over-cdp
- Electron transparent windows: https://www.electronjs.org/docs/latest/tutorial/transparent-windows