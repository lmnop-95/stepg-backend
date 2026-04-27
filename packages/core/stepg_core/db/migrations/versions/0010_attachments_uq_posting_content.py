"""add UniqueConstraint(posting_id, content_hash) on attachments.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-27 05:51:50.966009+00:00

M2 commit 5 — cron 재실행마다 같은 (posting_id, content_hash)가 무조건 INSERT되어
DB row N×duplicate 폭발하던 문제 차단 (Pass 8 critic Finding A). caller는
`pg_insert(Attachment)...on_conflict_do_nothing(index_elements=["posting_id",
"content_hash"])` 패턴으로 idempotent 보장 (Posting upsert와 동형). FS dedup은
LocalFsBackend.put_path가 이미 처리.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_attachments_posting_content",
        "attachments",
        ["posting_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_attachments_posting_content",
        "attachments",
        type_="unique",
    )
