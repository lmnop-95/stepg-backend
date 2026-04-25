import logging
from typing import Any

from arq.connections import RedisSettings
from stepg_core.core.config import settings
from stepg_core.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> None:
    logger.info("worker heartbeat")


class WorkerSettings:
    functions = [heartbeat]
    redis_settings = RedisSettings.from_dsn(settings.redis_url.get_secret_value())

    @staticmethod
    async def on_startup(ctx: dict[str, Any]) -> None:
        configure_logging()
