"""PDF (.pdf) parser — `pdfplumber` 1차 + `easyocr` fallback (M3 commit 3 SoT).

Commit 1 stub — `parse` 본문은 commit 3 에서 채움. fallback trigger 임계값은
env `PDF_OCR_FALLBACK_MIN_CHARS_PER_PAGE` (default 50). per-page OCR timeout
120s + per-document 1800s + cron 7200s budget 안에서 동작 (plan Q1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from stepg_core.features.parsing.schemas import ParsedDocument


def parse(path: Path) -> ParsedDocument:
    raise NotImplementedError(f"pdf parse @ {path} — commit 3에서 구현")


__all__ = ["parse"]
