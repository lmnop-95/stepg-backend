from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from stepg_core.db.base import Base


class ProjectPostingMatch(Base):
    """Pre-computed match score per Project x Posting (M8 reconcile_matches upsert).

    JSONB columns (`component_scores`, `tag_result`) are intentionally typed as
    `Mapped[dict[str, Any]]` — strict shape (`MatchScore.component_scores`,
    `MatchScore.tag_result` per `docs/ARCHITECTURE.md §4.3`) is enforced at the
    M6 service boundary via Pydantic, not at the ORM layer.
    """

    __tablename__ = "project_posting_matches"

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    posting_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("postings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    final_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    component_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    tag_result: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
