"""Attachment parsing DTO (M3).

`ParsedDocument` is the M3 → M4 contract. Each parser
(`parsers/{hwpx,pdf,docx}.py`) returns this; `service.parse_attachment`
splits sections and returns the same shape with `sections` populated.

`paragraphs` is in-memory only — splitter input. Persistence target on
`Attachment` is `extracted_text` (= `text`) + `sections`. paragraph/page
boundary 보존이 splitter 정확도에 직결 (헤더-본문이 같은 줄에 섞이는 PDF
column layout 차단).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ParsedDocument(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    text: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)


__all__ = ["ParsedDocument"]
