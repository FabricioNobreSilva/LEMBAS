import os
import sys
from pathlib import Path
from loguru import logger

LOG_DIR = Path.home() / "HoleriTech" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "{time:YYYY-MM-DD}.log"

# Remove handler padrão
logger.remove()

# Handler para arquivo com rotação diária e retenção de 30 dias
logger.add(
    str(LOG_FILE),
    rotation="00:00",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    encoding="utf-8",
)

# Handler para stderr com nível WARNING+ (não polui stdout que é usado para JSON)
logger.add(
    sys.stderr,
    level="WARNING",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)


def get_log_path() -> str:
    """Retorna o caminho do arquivo de log do dia atual."""
    from datetime import date
    return str(LOG_DIR / f"{date.today().isoformat()}.log")


def get_log_dir() -> str:
    return str(LOG_DIR)
