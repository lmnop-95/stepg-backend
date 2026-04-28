import logging
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings
from stepg_core.core.config import get_settings
from stepg_core.core.logging import configure_logging
from stepg_core.features.ingestion.service import ingest_postings

logger = logging.getLogger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> None:  # noqa: ARG001 — ARQ ctx 시그니처 고정
    logger.info("worker heartbeat")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [heartbeat, ingest_postings]
    # UTC 17:00 = KST 02:00. ARQ `cron()`은 timezone 파라미터 없이 프로세스 local time을
    # 사용하므로 워커 프로세스는 TZ=UTC로 띄워야 한다 (CLAUDE.md Build & Test 섹션).
    # timeout=7200은 bizinfo 100건 × 평균 3 첨부 download + M3 parsing (HWPX/PDF/DOCX
    # 본문 추출 + easyocr OCR fallback per-doc 1800s budget) worst-case 흡수 (Q1/Q74).
    # functions 리스트의 `ingest_postings`는 default(300s) 유지 — manual enqueue는
    # Phase 1까지 발생 안 함. max_tries=1 (default): cron 자체는 1회. 재시도는 tenacity가
    # attachment/HTTP 단위 처리 (`core/http.py`). run_at_startup=False (default): rolling
    # deploy double-fire 방지 — dev 검증은 `await ingest_postings({})` 직접 호출 또는
    # ARQ CLI manual enqueue로 (cron 발화 대기 불요).
    cron_jobs: ClassVar[list[Any]] = [
        cron(ingest_postings, hour={17}, minute=0, timeout=7200.0),
    ]
    # ARQ는 settings_cls.__dict__로 redis_settings를 읽어 디스크립터 프로토콜을 우회한다
    # (arq/worker.py: get_kwargs). 따라서 lazy 평가가 불가하며 import 시점에 RedisSettings를 만든다.
    # 테스트는 REDIS_URL을 setenv 후 get_settings.cache_clear()를 호출하기 전에 worker 모듈을 import해야 한다.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url.get_secret_value())

    @staticmethod
    async def on_startup(ctx: dict[str, Any]) -> None:  # noqa: ARG004 — ARQ ctx 시그니처 고정
        configure_logging()
