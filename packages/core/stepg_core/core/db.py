from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stepg_core.core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    s = get_settings()
    return create_async_engine(
        s.database_url.get_secret_value(),
        echo=s.app_env == "development",
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
