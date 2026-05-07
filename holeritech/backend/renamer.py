"""
renamer.py — Processamento em lote: extração, renomeação e cópia de PDFs.
"""

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from loguru import logger
from models import FileResult, ProcessSummary
from extractor import extract_digital, extract_ocr
from logger import get_log_path


def _unique_dest_path(dest_dir: Path, filename: str) -> Path:
    """Retorna um caminho único adicionando sufixo numérico se necessário."""
    dest = dest_dir / filename
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    counter = 2
    while True:
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def process_files(
    input_paths: list[str],
    output_dir: str,
    on_progress: Optional[Callable[[FileResult, int, int], None]] = None,
    extraction_mode: str = "auto",
    on_conflict: str = "suffix",
) -> ProcessSummary:
    """
    Processa uma lista de PDFs: extrai nome+CPF, renomeia e copia para output_dir.

    Args:
        input_paths: Lista de caminhos de PDFs.
        output_dir: Diretório de destino.
        on_progress: Callback chamado após cada arquivo processado.
        extraction_mode: "auto" | "digital" | "ocr"
        on_conflict: "suffix" | "overwrite" | "skip"

    Returns:
        ProcessSummary com estatísticas e resultados.
    """
    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    summary = ProcessSummary(
        total=len(input_paths),
        log_path=get_log_path(),
    )

    for idx, path_str in enumerate(input_paths, start=1):
        src = Path(path_str)
        result = FileResult(
            original_path=str(src),
            original_name=src.name,
        )

        # --- Extração conforme modo escolhido ---
        data = None
        if extraction_mode in ("auto", "digital"):
            data = extract_digital(str(src))
            if data:
                result.method = "digital"

        if data is None and extraction_mode in ("auto", "ocr"):
            data = extract_ocr(str(src))
            if data:
                result.method = "ocr"
                result.ocr_confidence = data.get("confidence")

        if data:
            new_filename = f"{data['nome']} - {data['cpf']}.pdf"
            dest_path = dest_dir / new_filename

            # --- Trata conflito de nome ---
            if dest_path.exists():
                if on_conflict == "skip":
                    result.status = "warning"
                    result.new_name = new_filename
                    result.error_message = "Arquivo já existe no destino — pulado."
                    logger.warning(f"{src.name} → pulado (já existe: {new_filename})")
                    summary.warnings += 1
                    summary.results.append(result)
                    if on_progress:
                        on_progress(result, idx, len(input_paths))
                    continue
                elif on_conflict == "suffix":
                    dest_path = _unique_dest_path(dest_dir, new_filename)
                # on_conflict == "overwrite": usa dest_path como está

            try:
                shutil.copy2(str(src), str(dest_path))
                result.new_name = dest_path.name
                result.status = "warning" if result.method == "ocr" else "success"

                method_tag = f"ocr (confiança: {result.ocr_confidence}%)" if result.method == "ocr" else "digital"
                logger.info(f"{src.name} → {dest_path.name} [{method_tag}]")

                if result.status == "success":
                    summary.success += 1
                else:
                    summary.warnings += 1

            except OSError as e:
                result.status = "error"
                result.error_message = f"Erro ao copiar arquivo: {e}"
                logger.error(f"{src.name} → falha na cópia: {e}")
                summary.errors += 1
        else:
            result.status = "error"
            result.error_message = "Falha na extração: nome ou CPF não encontrado"
            logger.error(f"{src.name} → falha na extração: nome ou CPF não encontrado")
            summary.errors += 1

        summary.results.append(result)

        if on_progress:
            on_progress(result, idx, len(input_paths))

    return summary
