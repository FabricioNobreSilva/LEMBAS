from dataclasses import dataclass, field
from typing import Literal


@dataclass
class FileResult:
    original_path: str
    original_name: str
    new_name: str | None = None
    status: Literal["success", "warning", "error"] = "error"
    method: Literal["digital", "ocr", "none"] = "none"
    ocr_confidence: float | None = None
    error_message: str | None = None


@dataclass
class ProcessSummary:
    total: int = 0
    success: int = 0
    warnings: int = 0
    errors: int = 0
    log_path: str = ""
    results: list[FileResult] = field(default_factory=list)


@dataclass
class UpdateInfo:
    current_version: str
    new_version: str
    download_url: str
    release_notes: str
    release_page_url: str
