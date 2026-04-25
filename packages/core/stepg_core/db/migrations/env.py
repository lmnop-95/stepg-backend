import asyncio
import re
from logging.config import fileConfig
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from stepg_core.core.config import settings

if TYPE_CHECKING:
    from alembic.operations.ops import MigrationScript
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import Connection
    from sqlalchemy.sql.schema import MetaData

config = context.config

config.set_main_option("sqlalchemy.url", settings.database_url.get_secret_value())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata: MetaData | None = None

_REV_ID_PATTERN = re.compile(r"^(\d{4})_")
_AUTO_HEX_REV_ID = re.compile(r"^[a-f0-9]{12}$")


def _next_padded_rev_id() -> str:
    versions_dir = Path(__file__).parent / "versions"
    nums = [
        int(m.group(1)) for p in versions_dir.glob("*.py") if (m := _REV_ID_PATTERN.match(p.name))
    ]
    return f"{(max(nums) + 1) if nums else 1:04d}"


def _pad_revision_id(
    _context: MigrationContext,
    _revision: object,
    directives: list[MigrationScript],
) -> None:
    if not directives:
        return
    rev_id = directives[0].rev_id
    if rev_id is not None and _AUTO_HEX_REV_ID.match(rev_id):
        directives[0].rev_id = _next_padded_rev_id()


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations_sync(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_pad_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    connectable = async_engine_from_config(section, prefix="sqlalchemy.")
    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations_sync)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
