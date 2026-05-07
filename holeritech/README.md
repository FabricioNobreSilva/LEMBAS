# HoleriTech

**Renomeação automática de holerites em PDF para uso corporativo interno.**

HoleriTech extrai automaticamente o nome do colaborador e o CPF de cada PDF de holerite e renomeia os arquivos no padrão `Nome Completo - CPF.pdf`, com suporte a PDFs digitais e escaneados (OCR).

---

## Funcionalidades

- Suporte a PDFs com texto selecionável (extração digital via `pdfplumber`)
- Fallback automático para OCR em PDFs escaneados (`pytesseract`)
- Processamento em lote de pastas inteiras
- Seletor de pasta de destino
- Barra de progresso em tempo real
- Tabela de resultados com status por arquivo
- Log diário com rotação automática (30 dias)
- Verificação de atualizações via GitHub Releases (não obrigatória)
- Funciona 100% offline
- Sem instalação de Python necessária (tudo empacotado)

---

## Pré-requisitos para Desenvolvimento

| Ferramenta | Versão mínima |
|---|---|
| Node.js | 20+ |
| Rust | 1.77+ (stable) |
| Python | 3.11+ |
| npm | 9+ |

> **Windows:** Instale também o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) e o [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/).

> **Linux (Ubuntu/Debian):** `sudo apt-get install libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libssl-dev pkg-config`

---

## Setup do Ambiente de Desenvolvimento

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/holeritech.git
cd holeritech

# 2. Instale dependências Node
npm install

# 3. Crie e ative o virtualenv Python
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# 4. Instale dependências Python
pip install -r backend/requirements.txt
pip install pyinstaller
```

---

## Rodando em Modo de Desenvolvimento

O modo dev **não** usa o sidecar Python compilado — requer que o backend seja iniciado separadamente.

### Terminal 1 — Frontend Tauri
```bash
npm run tauri dev
```

### Terminal 2 — Backend Python (para testes)
```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.\.venv\Scripts\Activate.ps1

cd backend
python main.py --mode check_update
python main.py --mode process --inputs '["caminho/holerite.pdf"]' --output "./saida"
```

> **Nota:** Em dev, o Tauri tentará usar o sidecar em `src-tauri/binaries/`. Para testar o fluxo completo, compile o backend primeiro (veja abaixo).

---

## Gerando Builds de Produção

### Passo 1 — Compilar o backend Python

**Linux / macOS:**
```bash
bash installer/build_backend.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File installer\build_backend.ps1
```

O executável será gerado em `src-tauri/binaries/` com o sufixo correto para a plataforma.

### Passo 2 — Gerar o instalador Tauri

**Linux / macOS:**
```bash
bash installer/build_app.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File installer\build_app.ps1
```

Os instaladores serão gerados em:
```
src-tauri/target/release/bundle/
  ├── msi/          # Windows — MSI
  ├── nsis/         # Windows — NSIS installer
  ├── dmg/          # macOS
  ├── deb/          # Linux
  └── appimage/     # Linux AppImage
```

---

## Publicando uma Nova Versão

1. Atualize a versão em `package.json` e `src-tauri/tauri.conf.json`
2. Atualize `CURRENT_VERSION` em `backend/updater.py`
3. Faça commit e crie uma tag semântica:

```bash
git add .
git commit -m "chore: bump version to v1.1.0"
git tag v1.1.0
git push origin main --tags
```

4. O GitHub Actions (`build.yml`) detectará a tag e:
   - Compilará para Windows, macOS (Intel + ARM) e Linux em paralelo
   - Criará automaticamente um GitHub Release com os instaladores como assets

> Configure os secrets `TAURI_SIGNING_PRIVATE_KEY` e `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` nas configurações do repositório para assinar os binários (opcional mas recomendado).

---

## Estrutura do Projeto

```
holeritech/
├── src-tauri/              # Shell Tauri (Rust mínimo)
│   ├── tauri.conf.json     # Configuração do app
│   ├── Cargo.toml
│   ├── build.rs
│   ├── binaries/           # Sidecar Python (gerado pelo build)
│   └── src/
│       ├── main.rs
│       └── lib.rs
├── src/                    # Frontend React + TypeScript
│   ├── App.tsx             # Componente raiz
│   ├── main.tsx
│   ├── components/
│   │   ├── DropZone.tsx
│   │   ├── DestinationPicker.tsx
│   │   ├── ProcessButton.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── ResultTable.tsx
│   │   └── LogViewer.tsx
│   ├── hooks/
│   │   └── useProcessor.ts # Comunicação com sidecar Python
│   ├── lib/
│   │   └── utils.ts
│   └── styles/
│       └── globals.css
├── backend/                # Backend Python
│   ├── main.py             # CLI entry point
│   ├── extractor.py        # Extração de nome + CPF
│   ├── renamer.py          # Renomeação e cópia
│   ├── logger.py           # Logs com loguru
│   ├── updater.py          # Verificação de atualização
│   ├── models.py           # Dataclasses
│   └── requirements.txt
├── installer/              # Scripts de build
│   ├── build_backend.sh
│   ├── build_backend.ps1
│   ├── build_app.sh
│   └── build_app.ps1
└── .github/
    └── workflows/
        └── build.yml       # CI/CD multiplataforma
```

---

## Padrão de Renomeação

```
{Nome Completo} - {CPF formatado}.pdf
```

**Exemplos:**
- `João Silva Santos - 123.456.789-00.pdf`
- `Ana Paula Ferreira - 987.654.321-00.pdf`

**Regras:**
- Nome em Title Case
- CPF sempre no formato `XXX.XXX.XXX-XX`
- Caracteres inválidos para nome de arquivo são removidos
- Se já existir arquivo com mesmo nome na pasta de destino, adiciona sufixo `(2)`, `(3)`, etc.

---

## Logs

Os logs são salvos em:
- **Windows:** `%USERPROFILE%\HoleriTech\logs\YYYY-MM-DD.log`
- **macOS / Linux:** `~/HoleriTech/logs/YYYY-MM-DD.log`

Formato de cada entrada:
```
2025-01-15 14:32:01 | INFO    | holerite_jan.pdf → João Silva - 123.456.789-00.pdf [digital]
2025-01-15 14:32:03 | WARNING | relatorio.pdf → Ana Souza - 987.654.321-00.pdf [ocr (confiança: 87.3%)]
2025-01-15 14:32:05 | ERROR   | holerite_003.pdf → falha na extração: nome ou CPF não encontrado
```

Retenção: 30 dias com rotação diária automática.

---

## Licença

MIT
