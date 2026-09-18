#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start VELO 2.0 development environment
.DESCRIPTION
    Starts Ollama, Chrome with CDP, FastAPI backend, and Electron frontend.
    All dependencies installed to D drive.
.PARAMETER SkipBackend
    Skip starting the Python backend
.PARAMETER SkipFrontend
    Skip starting the Electron UI
.PARAMETER SkipChrome
    Skip launching Chrome with CDP
.PARAMETER SkipOllama
    Skip starting Ollama
.PARAMETER TextMode
    Open just the backend with text-input mode (no mic needed)
#>

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipChrome,
    [switch]$SkipOllama,
    [switch]$TextMode
)

$Root       = "D:\VELO2"
$VenvPython = "$Root\velo_core\.venv\Scripts\python.exe"
$VenvPip    = "$Root\velo_core\.venv\Scripts\pip.exe"

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        VELO 2.0  — Dev Launcher      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Prerequisite checks ──────────────────────────────────────────────────────
$errors = @()

if (-not (Get-Command node   -ErrorAction SilentlyContinue)) { $errors += "Node.js not found.  Install: winget install OpenJS.NodeJS" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $errors += "Python not found.   Install: winget install Python.Python.3.11" }
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment at $Root\velo_core\.venv ..." -ForegroundColor Yellow
    python -m venv "$Root\velo_core\.venv"
}

if ($errors) {
    Write-Host "`nPrerequisites missing:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
    exit 1
}

# ── Install/update Python deps ───────────────────────────────────────────────
Write-Host "📦 Checking Python dependencies..." -ForegroundColor Yellow
& $VenvPip install -r "$Root\velo_core\requirements.txt" -q --exists-action i
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Some packages failed to install. Check $Root\velo_core\requirements.txt" -ForegroundColor Yellow
}

# Install Playwright browsers if not already present
$PlaywrightBrowsers = "$Root\velo_core\.venv\Lib\site-packages\playwright"
if (Test-Path $PlaywrightBrowsers) {
    Write-Host "📦 Ensuring Playwright browsers are installed..." -ForegroundColor Yellow
    & "$Root\velo_core\.venv\Scripts\playwright.exe" install chromium 2>&1 | Out-Null
}

# ── Ollama ───────────────────────────────────────────────────────────────────
if (-not $SkipOllama) {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Write-Host "⚠️  Ollama not found. Install: winget install Ollama.Ollama" -ForegroundColor Yellow
    } else {
        $ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
        if (-not $ollamaProc) {
            Write-Host "🤖 Starting Ollama..." -ForegroundColor Green
            Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep 3
        } else {
            Write-Host "✅ Ollama already running" -ForegroundColor Green
        }
        $model = "llama3.1:8b"
        Write-Host "📥 Pulling model $model (skips if already present)..." -ForegroundColor Yellow
        ollama pull $model 2>&1 | Select-Object -Last 2
    }
}

# ── Chrome with CDP ───────────────────────────────────────────────────────────
if (-not $SkipChrome) {
    $chromePaths = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )
    $chromePath = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($chromePath) {
        $cdpPort     = 9222
        $userDataDir = "D:\ChromeDevProfile"
        if (-not (Test-Path $userDataDir)) { New-Item -ItemType Directory -Path $userDataDir | Out-Null }

        # Check if already running with CDP
        $cdpRunning = try { (Invoke-WebRequest "http://localhost:$cdpPort/json/version" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop).StatusCode -eq 200 } catch { $false }

        if (-not $cdpRunning) {
            Write-Host "🌐 Starting Chrome with CDP on port $cdpPort..." -ForegroundColor Green
            $chromeArgs = "--remote-debugging-port=$cdpPort", "--user-data-dir=`"$userDataDir`""
            Start-Process $chromePath -ArgumentList $chromeArgs -WindowStyle Normal
            Start-Sleep 3
        } else {
            Write-Host "✅ Chrome CDP already running on port $cdpPort" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠️  Chrome not found. Start manually:" -ForegroundColor Yellow
        Write-Host '   chrome.exe --remote-debugging-port=9222 --user-data-dir="D:\ChromeDevProfile"' -ForegroundColor Gray
    }
}

# ── Backend ───────────────────────────────────────────────────────────────────
$backendJob = $null
if (-not $SkipBackend) {
    Write-Host "`n🚀 Starting Backend (velo_core)..." -ForegroundColor Green
    $backendJob = Start-Job -Name "velo-backend" -ScriptBlock {
        param($python, $root)
        Set-Location "$root\velo_core"
        & $python -m velo_core.main
    } -ArgumentList $VenvPython, $Root -WorkingDirectory "$Root\velo_core"
    Start-Sleep 3

    # Quick health check
    $healthy = try {
        (Invoke-WebRequest "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop).StatusCode -eq 200
    } catch { $false }

    if ($healthy) {
        Write-Host "✅ Backend healthy at http://localhost:8000" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Backend starting (may take a moment for Whisper model to load)" -ForegroundColor Yellow
    }
}

# ── Frontend ──────────────────────────────────────────────────────────────────
$frontendJob = $null
if (-not $SkipFrontend -and -not $TextMode) {
    Write-Host "🎨 Starting Frontend (Electron + Vite)..." -ForegroundColor Green
    Set-Location "$Root\velo_ui"

    if (-not (Test-Path "$Root\velo_ui\node_modules")) {
        Write-Host "📦 Installing npm dependencies..." -ForegroundColor Yellow
        npm install
    }

    $frontendJob = Start-Job -Name "velo-frontend" -ScriptBlock {
        param($root)
        Set-Location "$root\velo_ui"
        npm run electron:dev
    } -ArgumentList $Root -WorkingDirectory "$Root\velo_ui"
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         VELO 2.0  Running  ✅        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:    http://localhost:8000"       -ForegroundColor Gray
Write-Host "  Health:     http://localhost:8000/health" -ForegroundColor Gray
Write-Host "  Text input: http://localhost:8000/input" -ForegroundColor Gray
Write-Host "  WebSocket:  ws://localhost:8000/ws"      -ForegroundColor Gray
Write-Host "  UI hotkey:  Ctrl+Space (text mode)"      -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor DarkGray
Write-Host ""

try {
    $jobs = @($backendJob, $frontendJob) | Where-Object { $_ -ne $null }
    if ($jobs) {
        while ($true) {
            $jobs | Receive-Job | Write-Host
            Start-Sleep 2
        }
    }
} finally {
    Write-Host "`n🛑 Stopping services..." -ForegroundColor Yellow
    $jobs = @($backendJob, $frontendJob) | Where-Object { $_ -ne $null }
    $jobs | Stop-Job
    $jobs | Remove-Job -Force
    Write-Host "Done." -ForegroundColor Green
}