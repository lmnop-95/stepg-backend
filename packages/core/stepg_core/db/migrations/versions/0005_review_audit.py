"""add ReviewQueueItem, ExtractionAuditLog tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26 12:17:59.230581+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction_audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("posting_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('AUTO_APPROVE', 'MANUAL_APPROVE', 'EDIT', 'MANUAL_INSERT', 'REJECT')",
            name=op.f("ck_extraction_audit_logs_action_allowed"),
        ),
        sa.CheckConstraint(
            "(action = 'MANUAL_INSERT') = (before IS NULL)",
            name=op.f("ck_extraction_audit_logs_before_null_iff_manual_insert"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_extraction_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["postings.id"],
            name=op.f("fk_extraction_audit_logs_posting_id_postings"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extraction_audit_logs")),
    )
    op.create_index(
        "ix_extraction_audit_logs_created_at",
        "extraction_audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_audit_logs_posting_id",
        "extraction_audit_logs",
        ["posting_id"],
        unique=False,
    )
    op.create_table(
        "review_queue_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("posting_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "reasons",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=16),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('PENDING', 'APPROVED', 'REJECTED')",
            name=op.f("ck_review_queue_items_state_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name=op.f("fk_review_queue_items_assigned_to_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["postings.id"],
            name=op.f("fk_review_queue_items_posting_id_postings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_queue_items")),
    )
    op.create_index(
        "ix_review_queue_items_posting_id",
        "review_queue_items",
        ["posting_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_queue_items_state",
        "review_queue_items",
        ["state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_review_queue_items_state", table_name="review_queue_items")
    op.drop_index("ix_review_queue_items_posting_id", table_name="review_queue_items")
    op.drop_table("review_queue_items")
    op.drop_index("ix_extraction_audit_logs_posting_id", table_name="extraction_audit_logs")
    op.drop_index("ix_extraction_audit_logs_created_at", table_name="extraction_audit_logs")
    op.drop_table("extraction_audit_logs")
