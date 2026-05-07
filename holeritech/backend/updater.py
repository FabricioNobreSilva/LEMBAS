"""
updater.py — Verificação e execução de atualização via GitHub Releases API.
"""

import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

import requests
from packaging.version import Version

from models import UpdateInfo

GITHUB_REPO = "FabricioNobreSilva/LEMBAS"
CURRENT_VERSION = "1.0.0"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _get_download_url(assets: list[dict]) -> Optional[str]:
    """Seleciona o asset de download correto para o SO atual."""
    system = platform.system()

    if system == "Windows":
        # Procura o instalador NSIS gerado pelo Tauri: *_x64-setup.exe ou *-setup.exe
        for asset in assets:
            name: str = asset.get("name", "")
            if name.endswith("-setup.exe") or name.endswith("_setup.exe"):
                return asset.get("browser_download_url")
        # Fallback: qualquer .exe que não seja o backend
        for asset in assets:
            name = asset.get("name", "")
            if name.endswith(".exe") and "backend" not in name.lower():
                return asset.get("browser_download_url")

    elif system == "Darwin":
        for asset in assets:
            if asset.get("name", "").endswith(".dmg"):
                return asset.get("browser_download_url")

    else:  # Linux
        for asset in assets:
            if asset.get("name", "").endswith(".deb"):
                return asset.get("browser_download_url")
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


def do_update(download_url: str, emit_fn: Callable[[str, dict], None]) -> None:
    """
    Baixa o instalador da nova versão e o executa silenciosamente.
    Emite eventos de progresso via emit_fn durante o processo.
    """
    tmp_path: Optional[Path] = None
    try:
        system = platform.system()
        if system == "Windows":
            suffix = ".exe"
        elif system == "Darwin":
            suffix = ".dmg"
        else:
            suffix = ".deb"

        emit_fn("update_progress", {
            "step": "downloading",
            "percent": 0,
            "message": "Baixando atualização...",
        })

        response = requests.get(download_url, stream=True, timeout=180)
        response.raise_for_status()

        total_bytes = int(response.headers.get("content-length", 0))
        downloaded = 0

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            for chunk in response.iter_content(chunk_size=65536):
                tmp_file.write(chunk)
                downloaded += len(chunk)
                if total_bytes > 0:
                    pct = int(downloaded * 100 / total_bytes)
                    emit_fn("update_progress", {
                        "step": "downloading",
                        "percent": pct,
                        "message": f"Baixando... {pct}%",
                    })

        emit_fn("update_progress", {
            "step": "installing",
            "percent": 100,
            "message": "Iniciando instalação silenciosa...",
        })

        if system == "Windows":
            # /S = silent install (NSIS). O instalador fecha o app e substitui os arquivos.
            subprocess.Popen(
                [str(tmp_path), "/S"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        elif system == "Darwin":
            subprocess.Popen(["open", str(tmp_path)])
        else:
            subprocess.Popen(["pkexec", "dpkg", "-i", str(tmp_path)])

        emit_fn("update_started", {
            "message": "Instalação iniciada. O aplicativo será atualizado e reiniciado automaticamente.",
        })

    except requests.exceptions.Timeout:
        emit_fn("error", {"message": "Tempo esgotado ao baixar a atualização. Verifique a conexão."})
    except requests.exceptions.ConnectionError:
        emit_fn("error", {"message": "Sem conexão com a internet para baixar a atualização."})
    except Exception as exc:
        emit_fn("error", {"message": f"Falha ao aplicar atualização: {exc}"})
    finally:
        # Limpa o arquivo temporário apenas em caso de erro (em sucesso o instalador usa o arquivo)
        pass
