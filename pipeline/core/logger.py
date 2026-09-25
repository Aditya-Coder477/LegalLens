"""
pipeline/core/logger.py
=======================
Structured logging for the LegalLens pipeline.

Writes to:
  - legal-data/logs/download.log    (download events)
  - legal-data/logs/processing.log  (extraction, classification, dedup events)
  - Console (rich coloured output)

Usage:
    from pipeline.core.logger import get_logger
    log = get_logger("india_code")
    log.info("Downloaded act", url="https://...", sha256="abc...")
    log.error("Download failed", url="https://...", reason="HTTP 403")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# ── Internal console (stderr so it doesn't pollute piped output) ──
_console = Console(stderr=True, highlight=True)

# ── Log file paths ────────────────────────────────────────────────
_LOG_DIR: Path | None = None
_download_handler: logging.FileHandler | None = None
_processing_handler: logging.FileHandler | None = None
_initialised: bool = False


def _ensure_init(log_dir: str = "legal-data/logs") -> None:
    global _LOG_DIR, _download_handler, _processing_handler, _initialised
    if _initialised:
        return
    _LOG_DIR = Path(log_dir)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    _download_handler = logging.FileHandler(
        _LOG_DIR / "download.log", encoding="utf-8"
    )
    _download_handler.setFormatter(fmt)
    _download_handler.setLevel(logging.DEBUG)

    _processing_handler = logging.FileHandler(
        _LOG_DIR / "processing.log", encoding="utf-8"
    )
    _processing_handler.setFormatter(fmt)
    _processing_handler.setLevel(logging.DEBUG)

    _initialised = True


class PipelineLogger:
    """
    Thin wrapper that logs to both file handlers and the rich console.
    Accepts arbitrary **kwargs which are appended to the message as key=value pairs.
    """

    def __init__(self, name: str, log_dir: str = "legal-data/logs") -> None:
        _ensure_init(log_dir)
        self._name = name
        self._py_logger = logging.getLogger(f"legallens.{name}")
        self._py_logger.setLevel(logging.DEBUG)

        if not self._py_logger.handlers:
            # Rich console handler
            rich_handler = RichHandler(
                console=_console,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
            )
            rich_handler.setLevel(logging.INFO)
            self._py_logger.addHandler(rich_handler)

            # File handlers
            if _download_handler:
                self._py_logger.addHandler(_download_handler)
            if _processing_handler:
                self._py_logger.addHandler(_processing_handler)

        self._py_logger.propagate = False

    def _fmt(self, msg: str, **kwargs: Any) -> str:
        if kwargs:
            pairs = " | ".join(f"{k}={v!r}" for k, v in kwargs.items())
            return f"{msg} | {pairs}"
        return msg

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._py_logger.debug(self._fmt(msg, **kwargs))

    def info(self, msg: str, **kwargs: Any) -> None:
        self._py_logger.info(self._fmt(msg, **kwargs))

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._py_logger.warning(self._fmt(msg, **kwargs))

    def error(self, msg: str, **kwargs: Any) -> None:
        self._py_logger.error(self._fmt(msg, **kwargs))

    def critical(self, msg: str, **kwargs: Any) -> None:
        self._py_logger.critical(self._fmt(msg, **kwargs))

    # ── Convenience helpers for the pipeline ─────────────────────

    def log_download_success(self, url: str, local_path: str, sha256: str, size_bytes: int) -> None:
        self.info(
            "[DOWNLOADED]",
            url=url, local_path=local_path,
            sha256=sha256[:12] + "...", size_bytes=size_bytes
        )

    def log_download_failed(self, url: str, reason: str, http_status: int | None = None) -> None:
        self.error(
            "[FAILED]",
            url=url, reason=reason, http_status=http_status
        )

    def log_skipped(self, url: str, reason: str) -> None:
        self.info("[SKIPPED]", url=url, reason=reason)

    def log_duplicate(self, url: str, sha256: str) -> None:
        self.info("[DUPLICATE]", url=url, sha256=sha256[:12] + "...")

    def log_ocr(self, document_id: str, page: int, confidence: float | None) -> None:
        self.info(
            "[OCR]",
            document_id=document_id, page=page, confidence=confidence
        )


def get_logger(name: str, log_dir: str = "legal-data/logs") -> PipelineLogger:
    """
    Get or create a named pipeline logger.

    Args:
        name: Component name, e.g. 'india_code', 'pdf_extractor'.
        log_dir: Path to the logs directory.

    Returns:
        PipelineLogger instance.
    """
    return PipelineLogger(name, log_dir=log_dir)
