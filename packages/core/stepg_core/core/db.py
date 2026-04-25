from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from stepg_core.core.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

engine = create_async_engine(
    settings.database_url.get_secret_value(),
    echo=settings.app_env == "development",
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
