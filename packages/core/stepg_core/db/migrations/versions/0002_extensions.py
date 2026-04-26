"""enable ltree + pg_trgm + unaccent extensions.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-26 00:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_EXTENSIONS = ("ltree", "pg_trgm", "unaccent")


def upgrade() -> None:
    for ext in _EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}"')


def downgrade() -> None:
    for ext in reversed(_EXTENSIONS):
        op.execute(f'DROP EXTENSION IF EXISTS "{ext}"')
