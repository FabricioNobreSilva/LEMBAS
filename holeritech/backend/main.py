"""
main.py — Entry point CLI do backend HoleriTech.

Comunicação com o frontend Tauri via stdout (JSON line-by-line).
"""

import argparse
import io
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

# Força UTF-8 no stdout/stderr para compatibilidade com Tauri no Windows.
# Sem isso, Python usa o codepage do sistema (cp1252) e caracteres como ã/é
# produzem bytes inválidos que quebram o decodificador UTF-8 do Tauri.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# Garante que o diretório do script esteja no path (necessário no PyInstaller)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logger as _logger_setup  # Inicializa o logger ao importar
from loguru import logger
from models import FileResult, ProcessSummary
from renamer import process_files
from updater import check_for_updates, do_update
from logger import get_log_path, get_log_dir


def emit(event_type: str, data: dict) -> None:
    """Emite um evento JSON no stdout para o frontend Tauri consumir."""
    print(json.dumps({"type": event_type, "data": data}, ensure_ascii=False), flush=True)


def handle_process(args: argparse.Namespace) -> None:
    """Processa a lista de arquivos PDF e emite eventos de progresso."""
    try:
        input_paths: list[str] = json.loads(args.inputs)
        output_dir: str = args.output
        extraction_mode: str = getattr(args, "extraction_mode", "auto")
        on_conflict: str = getattr(args, "on_conflict", "suffix")
    except (json.JSONDecodeError, AttributeError) as e:
        emit("error", {"message": f"Parâmetros inválidos: {e}"})
        sys.exit(1)

    if not input_paths:
        emit("error", {"message": "Nenhum arquivo selecionado."})
        sys.exit(1)

    # Expande pastas para lista de PDFs
    expanded: list[str] = []
    for p in input_paths:
        path = Path(p)
        if path.is_dir():
            expanded.extend(str(f) for f in sorted(path.glob("*.pdf")))
            expanded.extend(str(f) for f in sorted(path.glob("*.PDF")))
        elif path.is_file() and path.suffix.lower() == ".pdf":
            expanded.append(str(path))

    if not expanded:
        emit("error", {"message": "Nenhum PDF encontrado nos caminhos fornecidos."})
        sys.exit(1)

    def on_progress(result: FileResult, current: int, total: int) -> None:
        emit("progress", {
            "current": current,
            "total": total,
            "filename": result.original_name,
        })
        emit("result", {
            "original_name": result.original_name,
            "new_name": result.new_name,
            "status": result.status,
            "method": result.method,
            "ocr_confidence": result.ocr_confidence,
            "error_message": result.error_message,
        })

    summary: ProcessSummary = process_files(
        input_paths=expanded,
        output_dir=output_dir,
        on_progress=on_progress,
        extraction_mode=extraction_mode,
        on_conflict=on_conflict,
    )

    emit("summary", {
        "total": summary.total,
        "success": summary.success,
        "warnings": summary.warnings,
        "errors": summary.errors,
        "log_path": summary.log_path,
        "log_dir": get_log_dir(),
    })


def handle_check_update() -> None:
    """Verifica atualizações disponíveis e emite o resultado."""
    update = check_for_updates()
    if update:
        emit("update_available", {
            "current_version": update.current_version,
            "new_version": update.new_version,
            "download_url": update.download_url,
            "release_notes": update.release_notes,
            "release_page_url": update.release_page_url,
        })
    else:
        emit("no_update", {"current_version": "1.0.7"})


def handle_get_log(args: argparse.Namespace) -> None:
    """Retorna o conteúdo do log do dia atual."""
    log_path = Path(get_log_path())
    content = ""
    if log_path.exists():
        try:
            content = log_path.read_text(encoding="utf-8")
        except OSError:
            content = "Não foi possível ler o arquivo de log."
    emit("log_content", {
        "path": str(log_path),
        "content": content,
        "log_dir": get_log_dir(),
    })


def handle_do_update(args: argparse.Namespace) -> None:
    """Baixa e instala a atualização silenciosamente."""
    download_url: str = getattr(args, "download_url", "")
    if not download_url:
        emit("error", {"message": "URL de download não fornecida."})
        sys.exit(1)
    do_update(download_url, emit)


def main() -> None:
    parser = argparse.ArgumentParser(description="HoleriTech Backend")
    parser.add_argument("--mode", required=True, choices=["process", "check_update", "get_log", "do_update"])
    parser.add_argument("--inputs", default="[]", help="JSON array de caminhos de entrada")
    parser.add_argument("--output", default="", help="Diretório de saída")
    parser.add_argument("--extraction-mode", default="auto", dest="extraction_mode",
                        choices=["auto", "digital", "ocr"], help="Modo de extração de texto")
    parser.add_argument("--on-conflict", default="suffix", dest="on_conflict",
                        choices=["suffix", "overwrite", "skip"], help="Ação ao haver conflito de nome")
    parser.add_argument("--download-url", default="", dest="download_url", help="URL do instalador para atualização")
    args = parser.parse_args()

    if args.mode == "process":
        handle_process(args)
    elif args.mode == "check_update":
        handle_check_update()
    elif args.mode == "get_log":
        handle_get_log(args)
    elif args.mode == "do_update":
        handle_do_update(args)


if __name__ == "__main__":
    main()
