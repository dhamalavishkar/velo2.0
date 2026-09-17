#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start VELO 2.0 development environment
#>

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipChrome
)

Write-Host "=== VELO 2.0 Development Environment ===" -ForegroundColor Cyan

# Check prerequisites
$errors = @()

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    $errors += "Ollama not found. Install: winget install Ollama.Ollama"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $errors += "Node.js not found. Install: winget install OpenJS.NodeJS"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $errors += "Python not found. Install: winget install Python.Python.3.11"
}

if ($errors) {
    Write-Host "Prerequisites missing:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

# Start Ollama if not running
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 3
}

# Pull model if needed
$model = "llama3.1:8b"
Write-Host "Ensuring model $model is available..." -ForegroundColor Yellow
ollama pull $model

# Start Chrome with CDP
if (-not $SkipChrome) {
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (Test-Path $chromePath) {
        $cdpPort = 9222
        $userDataDir = "C:\ChromeDevProfile"
        Write-Host "Starting Chrome with CDP on port $cdpPort..." -ForegroundColor Yellow
        if (-not (Test-Path $userDataDir)) { New-Item -ItemType Directory -Path $userDataDir | Out-Null }
        $args = "--remote-debugging-port=$cdpPort", "--user-data-dir=$userDataDir"
        Start-Process $chromePath -ArgumentList $args -WindowStyle Normal
        Start-Sleep 2
    } else {
        Write-Host "Chrome not found at $chromePath. Please start Chrome manually with:" -ForegroundColor Red
        Write-Host "  chrome.exe --remote-debugging-port=9222 --user-data-dir=`"C:\ChromeDevProfile`"" -ForegroundColor Gray
    }
}

# Start Backend
if (-not $SkipBackend) {
    Write-Host "Starting Backend (velo_core)..." -ForegroundColor Green
    Set-Location "D:\VELO2\velo_core"
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv .venv
    }
    & ".\.venv\Scripts\pip.exe" install -r requirements.txt -q
    $backendJob = Start-Job -ScriptBlock {
        & "D:\VELO2\velo_core\.venv\Scripts\python.exe" -m velo_core.main
    } -WorkingDirectory "D:\VELO2\velo_core"
}

# Start Frontend
if (-not $SkipFrontend) {
    Write-Host "Starting Frontend (velo_ui)..." -ForegroundColor Green
    Set-Location "D:\VELO2\velo_ui"
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
        npm install
    }
    $frontendJob = Start-Job -ScriptBlock {
        npm run dev
    } -WorkingDirectory "D:\VELO2\velo_ui"
}

Write-Host "`n=== VELO 2.0 Running ===" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Gray
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "WebSocket: ws://localhost:8000/ws" -ForegroundColor Gray
Write-Host "`nPress Ctrl+C to stop all services" -ForegroundColor Gray

try {
    if ($backendJob) { Wait-Job $backendJob }
    if ($frontendJob) { Wait-Job $frontendJob }
} catch {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    if ($backendJob) { Stop-Job $backendJob; Remove-Job $backendJob -Force }
    if ($frontendJob) { Stop-Job $frontendJob; Remove-Job $frontendJob -Force }
}