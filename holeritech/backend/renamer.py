"""
renamer.py — Processamento em lote: extração, renomeação e cópia de PDFs.
"""

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from loguru import logger
from models import FileResult, ProcessSummary
from extractor import (
    extract_digital,
    extract_ocr,
    is_per_page_employee_pdf,
    extract_digital_all_pages,
)
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


def _write_page(src_path: Path, page_index: int, dest_path: Path) -> None:
    """Escreve uma única página de um PDF no destino."""
    import pypdf
    reader = pypdf.PdfReader(str(src_path))
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[page_index])
    with open(str(dest_path), "wb") as f:
        writer.write(f)


def _resolve_dest(dest_dir: Path, new_filename: str, on_conflict: str) -> Optional[Path]:
    """
    Resolve o caminho de destino de acordo com a política de conflito.
    Retorna None se on_conflict=='skip' e o arquivo já existe.
    """
    dest_path = dest_dir / new_filename
    if dest_path.exists():
        if on_conflict == "skip":
            return None
        if on_conflict == "suffix":
            return _unique_dest_path(dest_dir, new_filename)
        # on_conflict == "overwrite": usa dest_path como está
    return dest_path


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

    # -----------------------------------------------------------------------
    # Fase 1: expande PDFs multi-funcionário para itens individuais
    # Cada item é (src, page_index_ou_None) onde page_index_ou_None=None
    # indica um PDF com um único funcionário (fluxo normal).
    # -----------------------------------------------------------------------
    work_items: list[tuple[Path, Optional[int]]] = []
    for path_str in input_paths:
        src = Path(path_str)
        if extraction_mode in ("auto", "digital") and is_per_page_employee_pdf(str(src)):
            pages_data = extract_digital_all_pages(str(src))
            if pages_data:
                for item in pages_data:
                    work_items.append((src, item["page_index"]))
            else:
                # PDF multi-página mas sem dados extraíveis — processa como arquivo único
                work_items.append((src, None))
        else:
            work_items.append((src, None))

    total = len(work_items)
    summary = ProcessSummary(
        total=total,
        log_path=get_log_path(),
    )

    # -----------------------------------------------------------------------
    # Fase 2: processa cada item
    # -----------------------------------------------------------------------
    for idx, (src, page_idx) in enumerate(work_items, start=1):
        result = FileResult(
            original_path=str(src),
            original_name=src.name,
        )

        # --- Extração ---
        data: Optional[dict] = None

        if page_idx is not None:
            # Item proveniente de PDF multi-funcionário — relê só a página necessária
            import pdfplumber as _pdfplumber
            from extractor import _extract_name_from_text, _extract_employee_code, CPF_PATTERN, _normalize_cpf
            try:
                with _pdfplumber.open(str(src)) as pdf:
                    text = pdf.pages[page_idx].extract_text() or ""
                lines = text.splitlines()
                cpf_raw = None
                cpf_line_idx = None
                for i, line in enumerate(lines):
                    m = CPF_PATTERN.search(line)
                    if m and "/" not in line[max(0, m.start() - 2):m.end() + 2]:
                        cpf_raw = m.group(0)
                        cpf_line_idx = i
                        break
                nome = _extract_name_from_text(text, cpf_line_idx, lines)
                if nome:
                    if cpf_raw:
                        data = {"nome": nome, "cpf": _normalize_cpf(cpf_raw), "id_type": "cpf"}
                    else:
                        codigo = _extract_employee_code(lines)
                        if codigo:
                            data = {"nome": nome, "cpf": f"Cod-{codigo}", "id_type": "codigo"}
                if data:
                    result.method = "digital"
            except Exception as exc:
                logger.error(f"Erro ao extrair pág. {page_idx} de '{src.name}': {exc}")
        else:
            # Fluxo normal: arquivo de um único funcionário
            if extraction_mode in ("auto", "digital"):
                data = extract_digital(str(src))
                if data:
                    result.method = "digital"

            if data is None and extraction_mode in ("auto", "ocr"):
                data = extract_ocr(str(src))
                if data:
                    result.method = "ocr"
                    result.ocr_confidence = data.get("confidence")

        # --- Gravação do arquivo de saída ---
        if data:
            new_filename = f"{data['nome']} - {data['cpf']}.pdf"
            dest_path = _resolve_dest(dest_dir, new_filename, on_conflict)

            if dest_path is None:
                # on_conflict == "skip"
                result.status = "warning"
                result.new_name = new_filename
                result.error_message = "Arquivo já existe no destino — pulado."
                logger.warning(f"{src.name} → pulado (já existe: {new_filename})")
                summary.warnings += 1
                summary.results.append(result)
                if on_progress:
                    on_progress(result, idx, total)
                continue

            try:
                if page_idx is not None:
                    _write_page(src, page_idx, dest_path)
                else:
                    shutil.copy2(str(src), str(dest_path))

                result.new_name = dest_path.name
                result.status = "warning" if result.method == "ocr" else "success"

                method_tag = (
                    f"ocr (confiança: {result.ocr_confidence}%)"
                    if result.method == "ocr"
                    else "digital"
                )
                page_tag = f" [pág. {page_idx + 1}]" if page_idx is not None else ""
                logger.info(f"{src.name}{page_tag} → {dest_path.name} [{method_tag}]")

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
            on_progress(result, idx, total)

    return summary
