"""Pytest configuration for golden 5 케이스 (`docs/PROMPTS.md §8` SoT).

`--run-golden` opt-in flag — real Anthropic API + DB 기반 manual run only. CI
에서 자동 collection 대상이지만 default skip (Phase 1 SOP "테스트 규칙 없음" + plan.md
commit 8 critic Q8 = `--run-golden` flag mechanism 채택).

Manual 실행:

    DATABASE_URL=... REDIS_URL=... ANTHROPIC_API_KEY=... \\
        uv run pytest tests/integration/extraction/test_golden.py --run-golden

Prerequisites:
- Postgres + Redis docker (`docker compose -f infra/docker-compose.dev.yml up -d`)
- alembic migrations applied (`uv run alembic upgrade head`)
- bizinfo 공고 데이터 적재 (`uv run arq stepg_worker.WorkerSettings` 또는 manual
  `await ingest_postings({})` — `PBLN_000000000121189` / `121184` / `121252` 3 케이스
  의존)
- `ANTHROPIC_API_KEY` 환경 변수 + sufficient credits
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from stepg_core.core.db import get_session_factory

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


def pytest_addoption(parser: pytest.Parser) -> None:
    """`--run-golden` opt-in flag — golden 5 케이스 활성화."""
    parser.addoption(
        "--run-golden",
        action="store_true",
        default=False,
        help="Run real Anthropic API + DB golden tests (opt-in, manual only)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """`golden` marker test 들 default skip — `--run-golden` 시만 실행."""
    if config.getoption("--run-golden"):
        return
    skip_golden = pytest.mark.skip(
        reason="real Anthropic API + DB integration test — opt-in via `--run-golden`"
    )
    for item in items:
        if "golden" in item.keywords:
            item.add_marker(skip_golden)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-test fresh AsyncSession — `extract_posting()` 가 내부 commit 하므로
    transactional rollback 패턴 미사용. cleanup 책임은 caller fixture (synthetic_*
    fixtures 가 본인 Posting delete + commit; bizinfo 케이스는 LLM 결과로 mutation
    잔존, M2 cron 의 hash-mismatch 재추출로 자연 갱신).
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
