import asyncio
import re
from logging.config import fileConfig
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from stepg_core.core.config import get_settings

if TYPE_CHECKING:
    from alembic.operations.ops import MigrationScript
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import Connection
    from sqlalchemy.sql.schema import MetaData

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata: MetaData | None = None

_cmd_opts = getattr(config, "cmd_opts", None)
if target_metadata is None and _cmd_opts is not None and getattr(_cmd_opts, "autogenerate", False):
    raise RuntimeError(
        "target_metadata가 None인 상태에서 --autogenerate를 호출했습니다. "
        "feature models를 stepg_core.db.base에 등록한 뒤 다시 시도하세요."
    )

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
        url=get_settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_pad_revision_id,
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
    connectable = create_async_engine(get_settings().database_url.get_secret_value())
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_run_migrations_sync)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
