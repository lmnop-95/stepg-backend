"""add Posting, Attachment, ProjectPostingMatch tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26 11:39:45.137335+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "postings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("eligibility", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("target_description", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("support_description", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            server_default=sa.text("''::tsvector"),
            nullable=False,
        ),
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
            "status IN ('ACTIVE', 'CLOSED', 'EXPIRED', 'DRAFT')",
            name=op.f("ck_postings_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_postings")),
        sa.UniqueConstraint("source", "source_id", name=op.f("uq_postings_source_dedup")),
    )
    op.create_index("ix_postings_deadline_at", "postings", ["deadline_at"], unique=False)
    op.create_index(
        "ix_postings_search_vector_gin",
        "postings",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_postings_title_trgm",
        "postings",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("posting_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["postings.id"],
            name=op.f("fk_attachments_posting_id_postings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
    )
    op.create_index("ix_attachments_content_hash", "attachments", ["content_hash"], unique=False)
    op.create_table(
        "posting_fields_of_work",
        sa.Column("posting_id", sa.BigInteger(), nullable=False),
        sa.Column("field_of_work_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_of_work_id"],
            ["fields_of_work.id"],
            name=op.f("fk_posting_fields_of_work_field_of_work_id_fields_of_work"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["postings.id"],
            name=op.f("fk_posting_fields_of_work_posting_id_postings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "posting_id", "field_of_work_id", name=op.f("pk_posting_fields_of_work")
        ),
    )
    op.create_table(
        "project_posting_matches",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("posting_id", sa.BigInteger(), nullable=False),
        sa.Column("final_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column(
            "component_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "tag_result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["postings.id"],
            name=op.f("fk_project_posting_matches_posting_id_postings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_posting_matches_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "posting_id", name=op.f("pk_project_posting_matches")
        ),
    )


def downgrade() -> None:
    op.drop_table("project_posting_matches")
    op.drop_table("posting_fields_of_work")
    op.drop_index("ix_attachments_content_hash", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index(
        "ix_postings_title_trgm",
        table_name="postings",
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.drop_index("ix_postings_search_vector_gin", table_name="postings", postgresql_using="gin")
    op.drop_index("ix_postings_deadline_at", table_name="postings")
    op.drop_table("postings")
