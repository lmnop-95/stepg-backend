"""ReviewQueueItem (M9 admin queue) + ExtractionAuditLog (append-only audit trail).

JSONB columns (`ExtractionAuditLog.before`, `after`) store snapshots of
`ExtractedPostingData` (`docs/ARCHITECTURE.md §4.2`). Strict shape is enforced
at the M9 service boundary via Pydantic; ORM hint is `dict[str, Any]` weak type.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from stepg_core.db.base import Base, TimestampMixin

REVIEW_STATES: tuple[str, ...] = ("PENDING", "APPROVED", "REJECTED")
"""M9 admin queue 워크플로 상태. Phase 1 1인 큐레이터라 IN_REVIEW 생략 (Q67)."""

_REVIEW_STATE_CHECK_SQL = f"state IN ({', '.join(repr(s) for s in REVIEW_STATES)})"

AUDIT_ACTIONS: tuple[str, ...] = (
    "AUTO_APPROVE",
    "MANUAL_APPROVE",
    "EDIT",
    "MANUAL_INSERT",
    "REJECT",
)
"""ExtractionAuditLog mutation 종류. AUTO vs MANUAL 구분이 audit context (Q72)."""

_AUDIT_ACTION_CHECK_SQL = f"action IN ({', '.join(repr(a) for a in AUDIT_ACTIONS)})"


class ReviewQueueItem(Base, TimestampMixin):
    """Low-confidence Posting을 admin이 검수할 큐 (M9).

    Lifecycle:
    - state: PENDING(생성 직후) → APPROVED 또는 REJECTED.
    - assigned_to: NULL = unassigned, set = 큐레이터 self-assign.
    - reasons: M4가 분기 사유를 ARRAY로 기록 (invalid 태그, low confidence 등).
    """

    __tablename__ = "review_queue_items"
    __table_args__ = (
        CheckConstraint(_REVIEW_STATE_CHECK_SQL, name="state_allowed"),
        Index("ix_review_queue_items_state", "state"),
        Index("ix_review_queue_items_posting_id", "posting_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    posting_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("postings.id", ondelete="CASCADE"),
        nullable=False,
    )
    reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="PENDING",
        server_default=text("'PENDING'"),
    )
    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ExtractionAuditLog(Base):
    """Append-only audit log of every Posting mutation (M9 + M4 auto-approve).

    Phase 1은 service convention으로 immutability 유지 (Phase 1.5에서 DB-level
    REVOKE / role 분리 검토 — `docs/ARCHITECTURE.md §10`).

    `before` is NULL only for `MANUAL_INSERT` (no prior state); the
    `before_null_iff_manual_insert` CHECK enforces this invariant DB-side.
    `after` always holds the post-mutation snapshot, including REJECT
    (status=REJECTED + reason).

    `actor_user_id` NULL has two meanings: (a) SET NULL on user delete to
    preserve history; (b) `AUTO_APPROVE` actions where the actor is the
    system (M4 LLM extractor, M8 reconcile cron) — NULL from INSERT.
    `posting_id` is RESTRICT to prevent silent loss of audit trail.
    """

    __tablename__ = "extraction_audit_logs"
    __table_args__ = (
        CheckConstraint(_AUDIT_ACTION_CHECK_SQL, name="action_allowed"),
        CheckConstraint(
            "(action = 'MANUAL_INSERT') = (before IS NULL)",
            name="before_null_iff_manual_insert",
        ),
        Index("ix_extraction_audit_logs_posting_id", "posting_id"),
        Index("ix_extraction_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    posting_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("postings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )


__all__ = [
    "AUDIT_ACTIONS",
    "REVIEW_STATES",
    "ExtractionAuditLog",
    "ReviewQueueItem",
]
