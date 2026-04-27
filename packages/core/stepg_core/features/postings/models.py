"""Posting / Attachment / posting↔FieldOfWork ORM.

JSONB columns (`Posting.eligibility`, `Posting.extracted_data`, `Posting.raw_payload`)
are intentionally typed as `Mapped[dict[str, Any] | None]` — strict shape
(`EligibilityRules` / `ExtractedPostingData` per `docs/ARCHITECTURE.md §4.1` /
§4.2) is enforced at the M4 service boundary via Pydantic, not at the ORM layer.

`raw_payload` is `nullable=True` at the schema level for safe gradual fill (M2 첫
ingest 전 기존 row 0건이지만 server_default 없이 add) — but M2 INSERT/upsert 코드
invariant는 NOT NULL (항상 source response dict를 박음). M4 read는 NULL 가드 없이
dict 가정. Phase 1.5에 `ALTER COLUMN raw_payload SET NOT NULL`로 schema-level 승격.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from stepg_core.db.base import Base, TimestampMixin

POSTING_STATUSES: tuple[str, ...] = ("ACTIVE", "CLOSED", "EXPIRED", "DRAFT")
"""§6.1 시스템 코드. SoT는 이 상수 — `_POSTING_STATUS_CHECK_SQL`이 SQL 표현 자동 생성."""

_POSTING_STATUS_CHECK_SQL = f"status IN ({', '.join(repr(s) for s in POSTING_STATUSES)})"


class Posting(Base, TimestampMixin):
    """Single grant posting.

    Lifecycle of nullable / placeholder columns:
    - `deadline_at`: NULL = LLM 추출 실패 또는 상시 모집. M6 Hard Filter는
      false-positive 편향(§6.1)으로 `IS NULL`을 통과시킴.
    - `eligibility` / `extracted_data`: NULL = M2 수집 직후, M4 추출 전.
      dict = M4 추출 완료. M6 Hard Filter는 `eligibility IS NULL`을 통과시킴.
    - `search_vector`: commit 5 BEFORE INSERT trigger가 자동 채움. server_default
      `''::tsvector`는 trigger 부재(개발/디버깅) 시 raw INSERT 안전망. ORM에서
      직접 read/write 금지(trigger가 덮어씀).
    """

    __tablename__ = "postings"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_postings_source_dedup"),
        CheckConstraint(_POSTING_STATUS_CHECK_SQL, name="status_allowed"),
        Index("ix_postings_search_vector_gin", "search_vector", postgresql_using="gin"),
        Index(
            "ix_postings_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("ix_postings_deadline_at", "deadline_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    eligibility: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    target_description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    support_description: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, nullable=False, server_default=text("''::tsvector")
    )


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("posting_id", "content_hash", name="uq_attachments_posting_content"),
        Index("ix_attachments_posting_id", "posting_id"),
        Index("ix_attachments_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    posting_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)


posting_fields_of_work = Table(
    "posting_fields_of_work",
    Base.metadata,
    Column(
        "posting_id",
        BigInteger,
        ForeignKey("postings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "field_of_work_id",
        PGUUID(as_uuid=True),
        ForeignKey("fields_of_work.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("ix_posting_fields_of_work_field_of_work_id", "field_of_work_id"),
)
"""Posting ↔ FieldOfWork N:M (M4 LLM extraction stores tag_ids here)."""


__all__ = ["POSTING_STATUSES", "Attachment", "Posting", "posting_fields_of_work"]
