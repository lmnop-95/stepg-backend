import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings
from stepg_core.core.config import get_settings
from stepg_core.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def heartbeat(_ctx: dict[str, Any]) -> None:
    logger.info("worker heartbeat")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [heartbeat]
    # ARQ는 settings_cls.__dict__로 redis_settings를 읽어 디스크립터 프로토콜을 우회한다
    # (arq/worker.py: get_kwargs). 따라서 lazy 평가가 불가하며 import 시점에 RedisSettings를 만든다.
    # 테스트는 REDIS_URL을 setenv 후 get_settings.cache_clear()를 호출하기 전에 worker 모듈을 import해야 한다.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url.get_secret_value())

    @staticmethod
    async def on_startup(_ctx: dict[str, Any]) -> None:
        configure_logging()
