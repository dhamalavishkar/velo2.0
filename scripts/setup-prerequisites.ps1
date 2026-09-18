#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install VELO 2.0 prerequisites: Ollama, Chrome CDP profile
#>

Write-Host "=== VELO 2.0 Prerequisites Setup ===" -ForegroundColor Cyan

# 1. Install Ollama
Write-Host "`n1. Installing Ollama..." -ForegroundColor Yellow
try {
    winget install --id Ollama.Ollama --source winget --accept-source-agreements --accept-package-agreements
    Write-Host "Ollama installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Winget failed, trying direct download..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile "$env:TEMP\OllamaSetup.exe"
        Start-Process -FilePath "$env:TEMP\OllamaSetup.exe" -ArgumentList "/S" -Wait
        Write-Host "Ollama installed via direct download" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to install Ollama. Please install manually from https://ollama.com/download" -ForegroundColor Red
    }
}

# 2. Start Ollama and pull model
Write-Host "`n2. Starting Ollama service..." -ForegroundColor Yellow
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 3
}

Write-Host "`n3. Pulling model llama3.1:8b (this may take a while)..." -ForegroundColor Yellow
ollama pull llama3.1:8b

# 4. Create Chrome CDP launcher script
Write-Host "`n4. Creating Chrome CDP launcher..." -ForegroundColor Yellow
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$cdpPort = 9222
$userDataDir = "C:\ChromeDevProfile"

if (-not (Test-Path $userDataDir)) {
    New-Item -ItemType Directory -Path $userDataDir | Out-Null
}

$launcherScript = @"
@echo off
echo Starting Chrome with CDP on port $cdpPort...
"$chromePath" --remote-debugging-port=$cdpPort --user-data-dir="$userDataDir"
"@

Set-Content -Path "D:\VELO2\scripts\launch-chrome-cdp.bat" -Value $launcherScript
Write-Host "Created launch-chrome-cdp.bat" -ForegroundColor Green

# 5. Porcupine access key reminder
Write-Host "`n5. Porcupine Access Key" -ForegroundColor Yellow
Write-Host "   Get free key at: https://picovoice.ai/" -ForegroundColor Gray
Write-Host "   Add to: D:\VELO2\velo_core\.env" -ForegroundColor Gray
Write-Host "   PORCUPINE_ACCESS_KEY=your_key_here" -ForegroundColor Gray

# 6. Verify
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
Write-Host "Ollama: $(if (Get-Command ollama -ErrorAction SilentlyContinue) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if (Get-Command ollama -ErrorAction SilentlyContinue) { 'Green' } else { 'Red' })
Write-Host "Chrome CDP Launcher: $(if (Test-Path "D:\VELO2\scripts\launch-chrome-cdp.bat") { 'CREATED' } else { 'FAILED' })" -ForegroundColor $(if (Test-Path "D:\VELO2\scripts\launch-chrome-cdp.bat") { 'Green' } else { 'Red' })
$envContent = Get-Content "D:\VELO2\velo_core\.env" -Raw
$hasKey = $envContent -match 'PORCUPINE_ACCESS_KEY=[^\s]+'
Write-Host "Porcupine Key: $(if ($hasKey) { 'SET' } else { 'NOT SET' })" -ForegroundColor $(if ($hasKey) { 'Green' } else { 'Red' })

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Run: .\scripts\launch-chrome-cdp.bat" -ForegroundColor Gray
Write-Host "2. Add Porcupine key to velo_core\.env" -ForegroundColor Gray
Write-Host "3. Run: .\scripts\dev.ps1" -ForegroundColor Gray