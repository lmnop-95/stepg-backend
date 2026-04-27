"""DOCX (.docx) parser — `python-docx` 기반 (M3 commit 4 SoT).

Commit 1 stub — `parse` 본문은 commit 4 에서 채움.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from stepg_core.features.parsing.schemas import ParsedDocument


def parse(path: Path) -> ParsedDocument:
    raise NotImplementedError(f"docx parse @ {path} — commit 4에서 구현")


__all__ = ["parse"]
