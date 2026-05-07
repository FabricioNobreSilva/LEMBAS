"""
updater.py — Verificação de atualização via GitHub Releases API.
"""

import platform
import sys
from typing import Optional

import requests
from packaging.version import Version

from models import UpdateInfo

GITHUB_REPO = "seu-usuario/holeritech"  # Substituir pelo repositório real
CURRENT_VERSION = "1.0.0"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Mapeamento de extensão de instalador por SO
INSTALLER_EXTENSIONS = {
    "Windows": ".msi",
    "Darwin": ".dmg",
    "Linux": ".deb",
}


def _get_download_url(assets: list[dict]) -> Optional[str]:
    """Seleciona o asset de download correto para o SO atual."""
    system = platform.system()
    ext = INSTALLER_EXTENSIONS.get(system, ".tar.gz")

    for asset in assets:
        name: str = asset.get("name", "")
        if name.endswith(ext):
            return asset.get("browser_download_url")

    # Fallback: .AppImage para Linux
    if system == "Linux":
        for asset in assets:
            if asset.get("name", "").endswith(".AppImage"):
                return asset.get("browser_download_url")

    return None


def check_for_updates(timeout: int = 5) -> Optional[UpdateInfo]:
    """
    Consulta a GitHub Releases API e retorna UpdateInfo se houver nova versão.

    Args:
        timeout: Tempo máximo de espera em segundos.

    Returns:
        UpdateInfo com dados da nova versão, ou None se não houver atualização.
    """
    try:
        response = requests.get(
            GITHUB_API_URL,
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        data = response.json()

        latest_tag: str = data.get("tag_name", "").lstrip("v")
        if not latest_tag:
            return None

        if Version(latest_tag) <= Version(CURRENT_VERSION):
            return None

        download_url = _get_download_url(data.get("assets", []))
        release_page_url: str = data.get("html_url", "")
        release_notes: str = data.get("body", "Sem notas de versão disponíveis.")

        return UpdateInfo(
            current_version=CURRENT_VERSION,
            new_version=latest_tag,
            download_url=download_url or release_page_url,
            release_notes=release_notes,
            release_page_url=release_page_url,
        )

    except requests.exceptions.ConnectionError:
        # Sem conexão — silencioso
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception:
        return None
