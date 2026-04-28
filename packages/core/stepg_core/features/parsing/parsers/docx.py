"""DOCX (.docx) parser — `python-docx` 기반 (M3 commit 4).

`Document.iter_inner_content()` 로 body 의 paragraph 와 table 을 document order
로 순회. table 은 `_Cell.iter_inner_content()` 로 재귀 진입해 nested table /
중첩 셀까지 모두 평탄화. 빈 paragraph 는 제거 (HWPX 패턴 일관). header /
footer 는 제외 — 본문만 추출.

License: MIT (`python-docx==1.2.0` PyPI METADATA + `LICENSE` 파일 직접 확인).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docx import Document
from docx.text.paragraph import Paragraph
from stepg_core.features.parsing.schemas import ParsedDocument

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from docx.table import Table


def _iter_paragraphs(items: Iterable[Paragraph | Table]) -> Iterator[Paragraph]:
    # body paragraph + nested table 셀 paragraph 평탄화 (rows / cols 구분 무시 —
    # M4 LLM 입력은 본문 의미만 필요, 표 구조 보존은 M9 admin queue escalation).
    # `_Cell.iter_inner_content()` 가 cell 안의 nested table 도 다시 yield 하므로
    # recursive 진입으로 모든 깊이 처리.
    for item in items:
        if isinstance(item, Paragraph):
            yield item
        else:
            for row in item.rows:
                for cell in row.cells:
                    yield from _iter_paragraphs(cell.iter_inner_content())


def parse(path: Path) -> ParsedDocument:
    # python-docx 1.2.0 type stub은 `str | IO[bytes] | None` 만 수용 (runtime은
    # path-like 직접 OK 이지만 pyright strict 통과 위해 명시 변환).
    document = Document(str(path))
    paragraphs = [
        stripped
        for paragraph in _iter_paragraphs(document.iter_inner_content())
        if (stripped := paragraph.text.strip())
    ]
    return ParsedDocument(
        text="\n\n".join(paragraphs),
        paragraphs=paragraphs,
    )


__all__ = ["parse"]
