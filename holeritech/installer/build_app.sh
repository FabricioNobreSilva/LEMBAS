#!/usr/bin/env bash
# installer/build_app.sh
# Gera o instalador desktop com Tauri.
# Deve ser executado APÓS build_backend.sh.
# Uso: bash installer/build_app.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== HoleriTech — Build Tauri App ==="

cd "$ROOT_DIR"

echo "→ Instalando dependências Node..."
npm install --silent

echo "→ Executando build Tauri..."
npm run tauri build

echo "=== Build do app concluído! ==="
echo "Instaladores gerados em: src-tauri/target/release/bundle/"
