"""HWPX (.hwpx) parser — `python-hwpx` 기반 (M3 commit 2).

`hwpx.TextExtractor.iter_document_paragraphs()` 로 모든 paragraph (table
포함, `include_nested=True` default) 를 순회하며 빈 줄을 제거한 뒤 `\\n\\n`
로 합본해서 `ParsedDocument` 반환.

ARCHITECTURE §1.1 deviation: 원래 `pyhwpx` 결정이었으나 그것은 Windows
COM + 한글 Office 의존이라 macOS / Linux Docker 환경 동작 불가. cross-platform
대안 `python-hwpx` (lxml 기반) 로 대체. PyPI v2.9.0 설치본 LICENSE는
"Custom Non-Commercial" (GitHub main 은 Apache 2.0) — Phase 1.5 SaaS 출시 전
maintainer 협상 / 자체 파서 전환 등 재검토 필요. 현재는 user 결정으로 위험 감수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hwpx import TextExtractor
from stepg_core.features.parsing.schemas import ParsedDocument

if TYPE_CHECKING:
    from pathlib import Path


def parse(path: Path) -> ParsedDocument:
    with TextExtractor(path) as extractor:
        paragraphs = [
            stripped
            for paragraph in extractor.iter_document_paragraphs()
            if (stripped := paragraph.text().strip())
        ]
    return ParsedDocument(
        text="\n\n".join(paragraphs),
        paragraphs=paragraphs,
    )


__all__ = ["parse"]
