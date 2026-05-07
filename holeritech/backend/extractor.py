"""
extractor.py — Extração de Nome e CPF de PDFs de holerites.

Modo 1: Extração digital via pdfplumber (PDFs com texto selecionável).
Modo 2: OCR via pdf2image + pytesseract (PDFs escaneados/imagem).
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional

import pdfplumber
from loguru import logger

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

CPF_PATTERN = re.compile(r"\b(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})[-\s]?(\d{2})\b")

NAME_LABEL_PATTERN = re.compile(
    r"(?:Nome\s*Completo|Funcion[aá]rio|Colaborador[a]?|Empregado[a]?|Nome)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)

# Tabela com cabeçalho "Código  Nome do Funcionário  CBO  ..."
TABLE_HEADER_PATTERN = re.compile(
    r"C[oó]digo\s+Nome\s+do\s+Funcion[aá]rio",
    re.IGNORECASE,
)

# Linha de dados da tabela: <código> <NOME EM MAIÚSCULAS> <CBO 6 dígitos> ...
TABLE_DATA_PATTERN = re.compile(
    r"^(\d{1,6})\s+([A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇ][A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇA-Za-záéíóúàâãêôõüç\s\-']{4,60}?)\s+\d{4,6}\b"
)

# Caracteres inválidos para nomes de arquivo (Windows + Unix)
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_cpf(raw: str) -> str:
    """Formata CPF para XXX.XXX.XXX-XX."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 11:
        return raw
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _is_valid_name(name: str) -> bool:
    """Valida nome: ao menos 2 palavras, apenas letras e espaços após normalização."""
    cleaned = re.sub(r"[^a-záéíóúàâãêôõüçA-ZÁÉÍÓÚÀÂÃÊÔÕÜÇ\s]", "", name).strip()
    words = cleaned.split()
    if len(words) < 2:
        return False
    if len(cleaned) < 5:
        return False
    return True


def _sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nome de arquivo e aplica Title Case."""
    name = INVALID_FILENAME_CHARS.sub("", name)
    name = name.strip()
    name = " ".join(name.split())  # normaliza espaços
    name = name.title()
    return name[:100]


def _extract_name_from_text(text: str, cpf_line_idx: int | None, lines: list[str]) -> Optional[str]:
    """
    Tenta extrair nome usando heurísticas:
    1. Procura rótulos inline (Nome: João)
    2. Procura cabeçalho de tabela "Código Nome do Funcionário" e lê a próxima linha
    3. Fallback: captura linha próxima ao CPF
    """
    # 1. Busca por rótulos inline em todas as linhas
    for line in lines:
        match = NAME_LABEL_PATTERN.search(line)
        if match:
            candidate = match.group(1).strip()
            candidate = re.split(r"\s{2,}|\t", candidate)[0].strip()
            # Não deixar que o próprio cabeçalho "CBO Departamento" vire nome
            if _is_valid_name(candidate) and not re.search(r"\b(CBO|Departamento|Filial|Cargo)\b", candidate, re.IGNORECASE):
                return _sanitize_filename(candidate)

    # 2. Cabeçalho de tabela "Código | Nome do Funcionário | CBO ..."
    for idx, line in enumerate(lines):
        if TABLE_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            data_line = lines[idx + 1].strip()
            m = TABLE_DATA_PATTERN.match(data_line)
            if m:
                candidate = m.group(2).strip()
                if _is_valid_name(candidate):
                    return _sanitize_filename(candidate)

    # 3. Fallback: linha adjacente ao CPF
    if cpf_line_idx is not None:
        for offset in range(-3, 4):
            adj = cpf_line_idx + offset
            if 0 <= adj < len(lines) and adj != cpf_line_idx:
                candidate = lines[adj].strip()
                candidate = re.sub(r"\d", "", candidate).strip()
                if _is_valid_name(candidate):
                    return _sanitize_filename(candidate)

    return None


def _extract_employee_code(lines: list[str]) -> Optional[str]:
    """Extrai o código numérico do funcionário da tabela quando não há CPF."""
    for idx, line in enumerate(lines):
        if TABLE_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            data_line = lines[idx + 1].strip()
            m = TABLE_DATA_PATTERN.match(data_line)
            if m:
                return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Modo 1 — Extração digital
# ---------------------------------------------------------------------------


def extract_digital(pdf_path: str) -> Optional[dict]:
    """
    Extrai nome e CPF de um PDF com texto selecionável usando pdfplumber.
    Retorna {"nome": str, "cpf": str, "id_type": "cpf"|"codigo"} ou None.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        if not full_text.strip():
            return None

        lines = full_text.splitlines()

        # Busca CPF
        cpf_raw = None
        cpf_line_idx = None
        for idx, line in enumerate(lines):
            m = CPF_PATTERN.search(line)
            if m:
                # Garante que não é CNPJ (14 dígitos com /)
                if "/" not in line[max(0, m.start()-2):m.end()+2]:
                    cpf_raw = m.group(0)
                    cpf_line_idx = idx
                    break

        # Busca nome
        nome = _extract_name_from_text(full_text, cpf_line_idx, lines)
        if not nome:
            logger.warning(f"Nome não encontrado (digital): {pdf_path}")
            return None

        if cpf_raw:
            cpf = _normalize_cpf(cpf_raw)
            return {"nome": nome, "cpf": cpf, "id_type": "cpf"}

        # Sem CPF: tenta usar o código do funcionário como identificador
        codigo = _extract_employee_code(lines)
        if codigo:
            logger.warning(f"CPF não encontrado, usando código '{codigo}': {pdf_path}")
            return {"nome": nome, "cpf": f"Cod-{codigo}", "id_type": "codigo"}

        logger.warning(f"CPF não encontrado (digital): {pdf_path}")
        return None

    except Exception as exc:
        logger.error(f"Erro extração digital '{pdf_path}': {exc}")
        return None


# ---------------------------------------------------------------------------
# Modo 2 — OCR
# ---------------------------------------------------------------------------


def extract_ocr(pdf_path: str) -> Optional[dict]:
    """
    Extrai nome e CPF de um PDF escaneado usando pdf2image + pytesseract.
    Retorna {"nome": str, "cpf": str, "confidence": float} ou None.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image, ImageFilter, ImageOps
        import numpy as np

        pages = convert_from_path(pdf_path, dpi=300)

        full_text = ""
        total_confidence = 0.0
        page_count = 0

        for page_img in pages[:3]:  # Processa no máximo 3 páginas
            # Pré-processamento
            gray = ImageOps.grayscale(page_img)

            # Binarização simples (threshold 128)
            threshold = 128
            binary = gray.point(lambda p: 255 if p > threshold else 0, "1")
            binary_rgb = binary.convert("RGB")

            # OCR com dados de confiança
            ocr_data = pytesseract.image_to_data(
                binary_rgb,
                lang="por",
                output_type=pytesseract.Output.DICT,
            )

            confidences = [
                int(c)
                for c in ocr_data["conf"]
                if str(c).lstrip("-").isdigit() and int(c) >= 0
            ]
            if confidences:
                total_confidence += sum(confidences) / len(confidences)
                page_count += 1

            page_text = pytesseract.image_to_string(binary_rgb, lang="por")
            full_text += page_text + "\n"

        avg_confidence = (total_confidence / page_count) if page_count > 0 else 0.0

        if not full_text.strip():
            return None

        lines = full_text.splitlines()

        # Busca CPF
        cpf_raw = None
        cpf_line_idx = None
        for idx, line in enumerate(lines):
            m = CPF_PATTERN.search(line)
            if m:
                cpf_raw = m.group(0)
                cpf_line_idx = idx
                break

        if not cpf_raw:
            logger.warning(f"CPF não encontrado (OCR): {pdf_path}")
            return None

        cpf = _normalize_cpf(cpf_raw)
        nome = _extract_name_from_text(full_text, cpf_line_idx, lines)

        if not nome:
            logger.warning(f"Nome não encontrado (OCR): {pdf_path}")
            return None

        return {"nome": nome, "cpf": cpf, "confidence": round(avg_confidence, 1)}

    except Exception as exc:
        logger.error(f"Erro OCR '{pdf_path}': {exc}")
        return None
