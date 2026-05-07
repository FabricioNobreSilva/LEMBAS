# installer/build_app.ps1
# Gera o instalador desktop com Tauri (Windows).
# Deve ser executado APÓS build_backend.ps1.
# Uso: powershell -ExecutionPolicy Bypass -File installer\build_app.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "=== HoleriTech — Build Tauri App (Windows) ===" -ForegroundColor Cyan

Set-Location $RootDir

Write-Host "→ Instalando dependências Node..." -ForegroundColor Yellow
npm install --silent

Write-Host "→ Executando build Tauri..." -ForegroundColor Yellow
npm run tauri build

Write-Host "=== Build do app concluído! ===" -ForegroundColor Cyan
Write-Host "Instaladores em: src-tauri\target\release\bundle\" -ForegroundColor Green
