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

# Tabela com cabeçalho "Código  Nome do Funcionário/Trabalhador  CBO  ..."
TABLE_HEADER_PATTERN = re.compile(
    r"C[oó]digo\s+Nome\s+do\s+(?:Funcion[aá]rio|[Tt]rabalhador)",
    re.IGNORECASE,
)

# Cabeçalho formato BRZ: "Matrícula  Nome"
MATRICULA_HEADER_PATTERN = re.compile(
    r"\bMatr[íi]cula\b.*\bNome\b",
    re.IGNORECASE,
)

# Linhas de rótulos de campos que NUNCA devem ser confundidas com nomes de pessoas
FIELD_LABEL_EXCLUSION_PATTERN = re.compile(
    r"\b(CPF|PIS|IRRF|INSS|Matr[íi]cula|Identidade|Contribui[çc][aã]o"
    r"|Sal[aá]rio|Banco|Ag[eê]ncia|Conta|Compet[eê]ncia|Admiss[aã]o"
    r"|Fun[çc][aã]o|Descri[çc][aã]o|Refer[eê]ncia|Vencimento|Desconto"
    r"|Sigla|Verba|C[Oo]ntrib|Período|Filial|Departamento|CBO)\b",
    re.IGNORECASE,
)

# Linha de dados da tabela: <código> <NOME EM MAIÚSCULAS> <CBO 6 dígitos> ...
TABLE_DATA_PATTERN = re.compile(
    r"^(\d{1,6})\s+([A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇ][A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇA-Za-záéíóúàâãêôõüç\s\-']{4,60}?)\s+\d{4,6}\b"
)

# Caracteres inválidos para nomes de arquivo (Windows + Unix)
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')

# Palavras que indicam linha de endereço (não devem ser confundidas com nomes)
ADDRESS_LINE_PATTERN = re.compile(
    r"\b(Rua|Av\.?|Avenida|Alameda|Travessa|Viela|Rodovia|Estr\.?|Estrada"
    r"|Bairro|CEP|Endere[çc]o|Logradouro|Cx\.?\s*Postal"
    r"|n[°º]?\.?\s*\d|Bloco|Apto\.?|Apartamento|Complemento)\b",
    re.IGNORECASE,
)

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
            # Não deixar que cabeçalhos ou endereços virem nome
            if (
                _is_valid_name(candidate)
                and not re.search(
                    r"\b(CBO|Departamento|Filial|Cargo|[Tt]rabalhador|Local\s+de)\b",
                    candidate, re.IGNORECASE
                )
                and not ADDRESS_LINE_PATTERN.search(candidate)
            ):
                return _sanitize_filename(candidate)

    # 2. Cabeçalho de tabela "Código | Nome do Funcionário/Trabalhador | CBO ..."
    for idx, line in enumerate(lines):
        if TABLE_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            nome_tabela, _ = _extract_from_table_line(lines[idx + 1].strip())
            if nome_tabela and _is_valid_name(nome_tabela):
                return _sanitize_filename(nome_tabela)

    # 2.5. Cabeçalho formato BRZ: "Matrícula Nome" + linha com <MATRÍCULA> <NOME COMPLETO>
    for idx, line in enumerate(lines):
        if MATRICULA_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            nome_mat, _ = _extract_from_matricula_line(lines[idx + 1].strip())
            if nome_mat and _is_valid_name(nome_mat):
                return _sanitize_filename(nome_mat)

    # 3. Fallback: linha adjacente ao CPF (prefere linhas ANTES, onde o nome costuma estar)
    if cpf_line_idx is not None:
        # Primeiro varre antes do CPF, depois depois — nomes precedem CPF na maioria dos layouts
        offsets = list(range(-1, -4, -1)) + list(range(1, 4))
        for offset in offsets:
            adj = cpf_line_idx + offset
            if not (0 <= adj < len(lines)):
                continue
            raw_line = lines[adj].strip()
            # Ignora linhas que parecem endereço antes mesmo de remover dígitos
            if ADDRESS_LINE_PATTERN.search(raw_line):
                continue
            candidate = re.sub(r"\d", "", raw_line).strip()
            # Remove pontuação residual típica de endereços (vírgulas, hífens soltos)
            candidate = re.sub(r"[,;]", " ", candidate).strip()
            candidate = " ".join(candidate.split())
            if (
                _is_valid_name(candidate)
                and not ADDRESS_LINE_PATTERN.search(candidate)
                and not FIELD_LABEL_EXCLUSION_PATTERN.search(raw_line)
            ):
                return _sanitize_filename(candidate)

    return None


# Partículas que podem aparecer em nomes brasileiros (não são abreviações de setor)
_NAME_PARTICLES = {'DA', 'DE', 'DO', 'DOS', 'DAS', 'E', 'DI', 'DEL', 'EM', 'NA', 'NO', 'NAS', 'NOS'}


def _extract_from_table_line(data_line: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrai (nome, código) de uma linha de dados de tabela de funcionários.
    Suporta dois formatos:
      - '22 DAVI MARINHO DA SILVA 317210 1 1'       (código CBO numérico após nome)
      - '323 FABRICIO NOBRE DA SILVA DHO - ALPHAVILLE' (local de trabalho após nome)
    """
    # Formato 1: código numérico CBO após o nome (padrão mais comum)
    m = TABLE_DATA_PATTERN.match(data_line)
    if m:
        return m.group(2).strip(), m.group(1)

    # Formato 2: departamento/local de trabalho após o nome (ex: "DHO - ALPHAVILLE")
    head = re.match(r'^(\d{1,6})\s+', data_line)
    if not head:
        return None, None
    code = head.group(1)
    rest = data_line[head.end():]

    name_words: list[str] = []
    for word in rest.split():
        # Para em dígito (código numérico) ou pontuação pura
        if re.match(r'^\d', word):
            break
        if not re.search(r'[A-Za-záéíóúàâãêôõüçÁÉÍÓÚÀÂÃÊÔÕÜÇ]', word):
            break
        upper = word.upper()
        # Palavra curta em maiúsculas que NÃO é partícula → provável abreviação de setor
        if name_words and len(word) <= 4 and word.isupper() and upper not in _NAME_PARTICLES:
            real = [w for w in name_words if w.upper() not in _NAME_PARTICLES]
            if len(real) >= 2:
                break
        name_words.append(word)

    if not name_words:
        return None, code
    return ' '.join(name_words), code


def _extract_from_matricula_line(data_line: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrai (nome, matrícula) de linha no formato BRZ: '<MATRÍCULA> <NOME COMPLETO>'.
    Exemplo: '00500039 FABIANO ALVES DE ALMEIDA SANTOS'
    """
    m = re.match(
        r'^(\d+)\s+([A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇ][A-ZÁÉÍÓÚÀÂÃÊÔÕÜÇA-Za-záéíóúàâãêôõüç\s\-\']+)',
        data_line.strip(),
    )
    if m:
        name = m.group(2).strip()
        if _is_valid_name(name):
            return name, m.group(1)
    return None, None


def _extract_employee_code(lines: list[str]) -> Optional[str]:
    """Extrai o código numérico do funcionário da tabela quando não há CPF."""
    for idx, line in enumerate(lines):
        if TABLE_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            _, code = _extract_from_table_line(lines[idx + 1].strip())
            if code:
                return code
        if MATRICULA_HEADER_PATTERN.search(line) and idx + 1 < len(lines):
            _, code = _extract_from_matricula_line(lines[idx + 1].strip())
            if code:
                return code
    return None


# ---------------------------------------------------------------------------
# Suporte a PDFs multi-funcionário (um funcionário por página)
# ---------------------------------------------------------------------------


def is_per_page_employee_pdf(pdf_path: str) -> bool:
    """
    Retorna True se o PDF parece ter um funcionário por página (ex: formato BRZ).
    Critério: cabeçalho 'Matrícula Nome' presente em pelo menos 2 das 4 primeiras páginas.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 2:
                return False
            headers_found = sum(
                1 for page in pdf.pages[:4]
                if MATRICULA_HEADER_PATTERN.search(page.extract_text() or "")
            )
            return headers_found >= 2
    except Exception:
        return False


def extract_digital_all_pages(pdf_path: str) -> list[dict]:
    """
    Para PDFs com um funcionário por página: extrai nome+CPF de cada página.
    Retorna lista de {"nome", "cpf", "id_type", "page_index"} para cada página com sucesso.
    """
    results: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                lines = text.splitlines()

                # Busca CPF
                cpf_raw = None
                cpf_line_idx = None
                for idx, line in enumerate(lines):
                    m = CPF_PATTERN.search(line)
                    if m and "/" not in line[max(0, m.start() - 2):m.end() + 2]:
                        cpf_raw = m.group(0)
                        cpf_line_idx = idx
                        break

                nome = _extract_name_from_text(text, cpf_line_idx, lines)
                if not nome:
                    logger.warning(f"Nome não encontrado na pág. {page_index}: {pdf_path}")
                    continue

                if cpf_raw:
                    item: dict = {
                        "nome": nome,
                        "cpf": _normalize_cpf(cpf_raw),
                        "id_type": "cpf",
                        "page_index": page_index,
                    }
                else:
                    codigo = _extract_employee_code(lines)
                    if codigo:
                        item = {
                            "nome": nome,
                            "cpf": f"Cod-{codigo}",
                            "id_type": "codigo",
                            "page_index": page_index,
                        }
                    else:
                        logger.warning(f"CPF e código não encontrados na pág. {page_index}: {pdf_path}")
                        continue

                results.append(item)
    except Exception as exc:
        logger.error(f"Erro na extração multi-página de '{pdf_path}': {exc}")
    return results


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
