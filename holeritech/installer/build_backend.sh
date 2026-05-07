#!/usr/bin/env bash
# installer/build_backend.sh
# Empacota o backend Python com PyInstaller.
# Uso: bash installer/build_backend.sh
# Requisito: Python 3.11+, pip, PyInstaller instalado no venv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"
DIST_DIR="$ROOT_DIR/src-tauri/binaries"

echo "=== HoleriTech — Build Backend Python ==="
echo "Raiz do projeto: $ROOT_DIR"

# Cria e ativa virtualenv se não existir
if [ ! -d "$ROOT_DIR/.venv" ]; then
  echo "→ Criando virtualenv..."
  python3 -m venv "$ROOT_DIR/.venv"
fi

source "$ROOT_DIR/.venv/bin/activate"

echo "→ Instalando dependências Python..."
pip install --upgrade pip --quiet
pip install -r "$BACKEND_DIR/requirements.txt" --quiet
pip install pyinstaller --quiet

echo "→ Empacotando com PyInstaller..."

# Detecta plataforma para sufixo do binário (exigido pelo Tauri)
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
  Linux*)
    SUFFIX="x86_64-unknown-linux-gnu"
    ;;
  Darwin*)
    if [ "$ARCH" = "arm64" ]; then
      SUFFIX="aarch64-apple-darwin"
    else
      SUFFIX="x86_64-apple-darwin"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    SUFFIX="x86_64-pc-windows-msvc"
    ;;
  *)
    SUFFIX="unknown"
    ;;
esac

BINARY_NAME="holeritech-backend-$SUFFIX"

mkdir -p "$DIST_DIR"

pyinstaller \
  --onefile \
  --name "$BINARY_NAME" \
  --distpath "$DIST_DIR" \
  --workpath "$ROOT_DIR/build/pyinstaller-work" \
  --specpath "$ROOT_DIR/build" \
  --hidden-import pdfplumber \
  --hidden-import pytesseract \
  --hidden-import pdf2image \
  --hidden-import PIL \
  --hidden-import loguru \
  --hidden-import requests \
  --hidden-import packaging \
  --hidden-import pypdf \
  --noconfirm \
  "$BACKEND_DIR/main.py"

echo "✓ Binário gerado: $DIST_DIR/$BINARY_NAME"
echo "=== Build backend concluído! ==="
