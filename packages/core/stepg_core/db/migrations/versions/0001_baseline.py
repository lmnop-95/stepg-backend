"""baseline (empty).

Revision ID: 0001
Revises:
Create Date: 2026-04-26 00:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise NotImplementedError(
        "0001_baseline downgrade is not supported (pre-launch policy). "
        "Reset dev DB via `docker compose -f infra/docker-compose.dev.yml down -v`."
    )
