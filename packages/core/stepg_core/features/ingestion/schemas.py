"""Source-agnostic boundary DTO for ingested postings (M2 Q26/Q46).

`RawPostingPayload` is the surface contract every source adapter
(`features/ingestion/sources/*.py`) returns. Adding a new source (k-startup,
Phase 1.5) only requires extending `SourceKind` and the `SOURCES` registry —
the DTO shape stays.

Legacy lessons (`docs/legacy/assets.md` §M2.2):
- `frozen=True` + `str_strip_whitespace=True` — read-only at the boundary.
- `raw_payload: dict[str, object]` carries source-specific fields (e.g.
  `bsnsSumryCn` 본문) without bloating the surface (legacy C2). Consumers must
  not mutate it; deep-copy if mutation is required.
- timezone-aware UTC validator centralizes KST → UTC conversion at the boundary
  (CLAUDE.md absolute rule A; legacy B1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceKind = Literal["bizinfo"]
"""Phase 1 = bizinfo only. Phase 1.5 extends with `"kstartup"`."""


class AttachmentRef(BaseModel):
    """Source-supplied attachment URL + display filename (Q81).

    `filename` carries the source's original name (e.g. bizinfo `fileNm` —
    `[공고문]_2026년_..._모집공고.hwpx`). Mime detection happens at download
    time via `mimetypes.guess_type(filename)` because public-agency
    `Content-Type` headers are unreliable. `url` is the absolute fetch URL;
    bizinfo serves attachments via `getImageFile.do?atchFileId=...&fileSn=...`.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    filename: str = Field(min_length=1)
    url: str = Field(min_length=1)


class RawPostingPayload(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    source: SourceKind
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    agency: str | None = None
    category: str | None = None
    support_amount_krw: int | None = Field(default=None, ge=0)
    apply_start_at: datetime | None = None
    apply_end_at: datetime | None = None
    detail_url: str | None = None
    attachments: tuple[AttachmentRef, ...] = ()
    raw_payload: dict[str, object]

    @field_validator("apply_start_at", "apply_end_at", mode="after")
    @classmethod
    def _require_timezone_aware_utc(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is None:
            raise ValueError("naive datetime은 허용되지 않습니다 — tzinfo 필수")
        return v.astimezone(UTC)


__all__ = ["AttachmentRef", "RawPostingPayload", "SourceKind"]
