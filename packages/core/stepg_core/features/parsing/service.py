"""Attachment parsing orchestrator (M3 commit 1 SoT).

Routes downloaded attachments to format-specific parsers by filename
suffix (lowercase, derived inside this function from the supplied
filename — caller need not normalize). MIME은 dispatch에 사용 안 함
(`mimetypes.guess_type`이 `.hwpx`를 `application/octet-stream`으로 인식
하므로 — Q7).

Pure function: 호출자(commit 6의 `parse_attachments`)가 ORM persistence
와 `parse_status` 마킹·logging을 책임진다. 본 함수는 routing + parse +
section splitting 만.

Exceptions as contract (Q6/Q7):
- `UnsupportedAttachmentFormatError`: suffix가 dispatch matrix에 없음
  → 호출자 `parse_status='skipped_unsupported'`.
- 그 외 parser raise: propagate → 호출자 `parse_status='failed'` +
  `parse_error=str(exc)`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

from stepg_core.core.errors import UnsupportedAttachmentFormatError
from stepg_core.features.parsing.parsers import docx as docx_parser
from stepg_core.features.parsing.parsers import hwpx as hwpx_parser
from stepg_core.features.parsing.parsers import pdf as pdf_parser
from stepg_core.features.parsing.schemas import ParsedDocument
from stepg_core.features.parsing.sections import split_sections

_ParserFn = Callable[[Path], ParsedDocument]

_DISPATCH: Final[dict[str, _ParserFn]] = {
    ".pdf": pdf_parser.parse,
    ".hwpx": hwpx_parser.parse,
    ".docx": docx_parser.parse,
}


def parse_attachment(filename: str, path: Path) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    parser = _DISPATCH.get(suffix)
    if parser is None:
        raise UnsupportedAttachmentFormatError(suffix=suffix, filename=filename)

    document = parser(path)
    sections = split_sections(document.paragraphs)
    return ParsedDocument(
        text=document.text,
        paragraphs=document.paragraphs,
        sections=sections,
    )


__all__ = ["parse_attachment"]
