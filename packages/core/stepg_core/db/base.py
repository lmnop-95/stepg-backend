"""SQLAlchemy declarative `Base` + naming convention + TimestampMixin.

`Base.metadata` is the single MetaData object Alembic autogenerate compares
against. Every feature module's `models.py` must be imported below so that
its mappers register on this MetaData.
"""

from datetime import UTC, datetime

from sqlalchemy import MetaData, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime

_NOW_UTC_SQL = "now()"
"""TIMESTAMPTZ 컬럼 server_default. Postgres `now()`는 timestamptz를 반환하며
session tz 무관하게 절대 UTC 모멘트를 저장."""

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
"""ORM `CheckConstraint(name="X")` should pass the SHORT name (no prefix); this
convention auto-prepends `ck_%(table_name)s_` so the migration emits e.g.
`ck_companies_X`. Same rule for `uq_`, `fk_`, `pk_`. Indexes use `ix_` and the
column label."""


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text(_NOW_UTC_SQL),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text(_NOW_UTC_SQL),
    )


def _register_feature_mappers() -> None:
    """Importing each feature `models` module registers its mappers on Base.metadata.

    Function-local imports avoid a circular import (feature modules import `Base` from here)
    and the module-level `E402` lint.

    NOTE: when adding a new feature module, add its import line below AND update
    `docs/.local/<branch>/plan.md` 작업 흐름. Missing import => autogenerate produces an
    empty diff for that table (silent miss).
    """
    import stepg_core.features.companies.models  # noqa: F401  # pyright: ignore[reportUnusedImport]
    import stepg_core.features.fields_of_work.models  # noqa: F401  # pyright: ignore[reportUnusedImport]
    import stepg_core.features.projects.models  # noqa: F401  # pyright: ignore[reportUnusedImport]
    import stepg_core.features.users.models  # noqa: F401  # pyright: ignore[reportUnusedImport]


_register_feature_mappers()
