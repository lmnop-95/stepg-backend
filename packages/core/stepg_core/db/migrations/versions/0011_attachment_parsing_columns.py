"""add Attachment parsing columns + attachment_parse_status ENUM type.

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-27 17:30:00.000000+00:00

M3 commit 1 — establishes the parse surface area on attachments.

Columns:
- `extracted_text TEXT NULL`: parsed body. NULL = parse 전 (Posting.eligibility/
  extracted_data 라이프사이클 패턴 답습).
- `sections JSONB NULL`: section splitter 산출 dict (영문 키). NULL = parse 전.
- `parse_status attachment_parse_status NOT NULL DEFAULT 'pending'`: 라이프사이클
  마커. 기존 row 백필도 'pending' (M3 cron 첫 발화에 자연 처리).
- `parse_error TEXT NULL`: status='failed' 일 때만 채움.

ENUM type `attachment_parse_status` 값: pending / ok / skipped_unsupported /
failed (`features/postings/models.py::ATTACHMENT_PARSE_STATUSES`가 SoT).

Round-trip test (`alembic upgrade head && downgrade -1 && upgrade head`)는
`postgresql.ENUM(...).drop(...)` 명시로 통과 — autogenerate가 ENUM drop을
안정적으로 잡지 못해 수동 명시.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARSE_STATUS_VALUES = ("pending", "ok", "skipped_unsupported", "failed")
_ENUM_NAME = "attachment_parse_status"


def upgrade() -> None:
    parse_status = postgresql.ENUM(
        *_PARSE_STATUS_VALUES,
        name=_ENUM_NAME,
        create_type=False,
    )
    parse_status.create(op.get_bind(), checkfirst=False)

    op.add_column(
        "attachments",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "attachments",
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "attachments",
        sa.Column(
            "parse_status",
            parse_status,
            nullable=False,
            server_default=sa.text("'pending'::attachment_parse_status"),
        ),
    )
    op.add_column(
        "attachments",
        sa.Column("parse_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attachments", "parse_error")
    op.drop_column("attachments", "parse_status")
    op.drop_column("attachments", "sections")
    op.drop_column("attachments", "extracted_text")

    parse_status = postgresql.ENUM(*_PARSE_STATUS_VALUES, name=_ENUM_NAME)
    parse_status.drop(op.get_bind(), checkfirst=False)
