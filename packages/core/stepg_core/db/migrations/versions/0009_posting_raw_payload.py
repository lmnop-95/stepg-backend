"""add Posting.raw_payload JSONB column.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-27 04:30:10.442777+00:00

M2 commit 3 — source 응답 dict 그대로 보존하는 컬럼. M4 LLM 추출이 단일 read로
원본 컨텍스트를 가져갈 수 있게 함 (legacy C2: 장문 본문 raw_payload만, 표면 DTO 금지).

`nullable=True` + server_default 없음 (Q24): M2 첫 ingest 전 기존 row 0건이라 backfill
불요. M2 INSERT/upsert 코드 invariant는 NOT NULL (항상 source response dict 박음),
M4 read는 NULL 가드 없이 dict 가정. Phase 1.5에 `ALTER COLUMN raw_payload SET NOT NULL`로
schema-level 승격.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "postings",
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("postings", "raw_payload")
