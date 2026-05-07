# installer/build_backend.ps1
# Empacota o backend Python com PyInstaller (Windows).
# Uso: powershell -ExecutionPolicy Bypass -File installer\build_backend.ps1

param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$DistDir = Join-Path $RootDir "src-tauri\binaries"
$VenvDir = Join-Path $RootDir ".venv"

Write-Host "=== HoleriTech — Build Backend Python (Windows) ===" -ForegroundColor Cyan
Write-Host "Raiz do projeto: $RootDir"

# Cria virtualenv
if (-not (Test-Path $VenvDir)) {
  Write-Host "→ Criando virtualenv..." -ForegroundColor Yellow
  & $PythonExe -m venv $VenvDir
}

$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
$PyInstallerExe = Join-Path $VenvDir "Scripts\pyinstaller.exe"

Write-Host "→ Instalando dependências Python..." -ForegroundColor Yellow
& $PipExe install --upgrade pip --quiet
& $PipExe install -r "$BackendDir\requirements.txt" --quiet
& $PipExe install pyinstaller --quiet

# Nome do binário com sufixo Tauri para Windows x86_64
$BinaryName = "holeritech-backend-x86_64-pc-windows-msvc.exe"

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

Write-Host "→ Empacotando com PyInstaller..." -ForegroundColor Yellow

$BuildWork = Join-Path $RootDir "build\pyinstaller-work"
$BuildSpec = Join-Path $RootDir "build"

& $PyInstallerExe `
  --onefile `
  --name ($BinaryName -replace "\.exe$", "") `
  --distpath $DistDir `
  --workpath $BuildWork `
  --specpath $BuildSpec `
  --hidden-import pdfplumber `
  --hidden-import pytesseract `
  --hidden-import pdf2image `
  --hidden-import PIL `
  --hidden-import loguru `
  --hidden-import requests `
  --hidden-import packaging `
  --hidden-import pypdf `
  --noconfirm `
  "$BackendDir\main.py"

Write-Host "✓ Binário gerado: $DistDir\$BinaryName" -ForegroundColor Green
Write-Host "=== Build backend concluído! ===" -ForegroundColor Cyan
