import logging
import os
from typing import Any

from arq.connections import RedisSettings

logger = logging.getLogger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> None:
    logger.info("worker heartbeat")


class WorkerSettings:
    functions = [heartbeat]
    redis_settings = RedisSettings.from_dsn(os.environ["REDIS_URL"])
