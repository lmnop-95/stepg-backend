"""M4.4 commit 3 — batch baseline measurement (n=bizinfo postings).

bypass `extract_postings_batch` + `asyncio.Semaphore` concurrency (Q28=1).
Stage 1 log handler 가 cache tokens parse → m4_baseline.md 안 hit ratio 적재 (F1 적용).
결과 → `docs/eval/m4_baseline.md` (F12 양식 — 표 + 서술).

Usage (default sequential, Q32=2 — Tier 1 ITPM 30K 안전):
    uv run python scripts/batch_baseline.py

Higher tier override (concurrency 환경변수 — F1 권장 양식):
    BASELINE_CONCURRENCY=10 uv run python scripts/batch_baseline.py

**Tier 1 ITPM 30K 한계 주의 (2026-05-03 발견)**: bizinfo posting 의 attachments
parse 본문 포함 per-call input ~34K avg → 단일 호출도 ITPM 초과 가능성. SDK
default retry+backoff (max_retries=2) 가 `retry-after` header 활용 회복 양식.

**Anthropic tier-aware concurrency 가이드** (env override 양식):

| Tier | ITPM | 권장 BASELINE_CONCURRENCY | 162건 ETA |
|------|------|---------------------------|-----------|
| 1 | 30K | 1 (sequential, default) | ~25-35분 |
| 2 | 80K | 3-5 | ~7-12분 |
| 3 | 200K | 10-15 | ~2-5분 |
| 4 | 400K | 15-20 | ~1-3분 |

Tier 1 default sequential 양식 = burst 회피 + cache TTL 5분 안 안전 (12-15s/call
x 162 < 5분 cache eviction 회복 cycle).

**Pre-run SOP** (F7 — optional rollback safety, 사용자 manual 실행, Q30=3):
    pg_dump --table=extraction_audit_logs --table=posting_fields_of_work \\
            stepg > snapshot_v1.sql

**Cost** (실측, 2026-05-03 n=162): ~$5.11 (input $0.39 + output $2.92 +
cache_read $1.67 + cache_write $0.13). per-posting baseline ≈ $0.03 (Sonnet 4.6,
bizinfo attachment dense). output token $15/M dominate — cache 효과 input only,
output cost 별도 산출 mandate.

**Phase 1.5 marker — log regex coupling (F33)**: 본 script 의
`_STAGE1_LOG_PATTERN` 가 `stage1.py:88` log message format parse → format 변경
시 dual-edit risk. 더 자주 사용되면 `extract_posting()` signature 안
`on_token_usage: Callable[[Usage], None] | None = None` callback 양식 마이그레이션
검토.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from stepg_core.core.db import get_engine
from stepg_core.core.logging import configure_logging
from stepg_core.features.extraction.service import (
    extract_posting,
    reset_posting_for_re_extraction,
)
from stepg_core.features.postings.models import (
    Attachment,
    Posting,
    posting_fields_of_work,
)
from stepg_core.features.review.models import ExtractionAuditLog

if TYPE_CHECKING:
    from collections.abc import Sequence


def _load_concurrency() -> int:
    """`BASELINE_CONCURRENCY` env 검증 — int + ≥1 (CodeRabbit #3178194334)."""
    raw = os.getenv("BASELINE_CONCURRENCY", "1")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"BASELINE_CONCURRENCY 값이 숫자가 아닙니다: {raw!r}") from exc
    if value < 1:
        raise ValueError(f"BASELINE_CONCURRENCY 는 1 이상의 정수여야 합니다: {value}")
    return value


_CONCURRENCY = _load_concurrency()
_TARGET_SOURCE = "bizinfo"
_LOW_CONF_THRESHOLD = 0.7
_OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "eval" / "m4_baseline.md"

# Stage 1 호출 성공 log message parse — `stage1.py:87` SoT mirror. format 변경 시
# 본 regex 동기 갱신 (cache_read/creation token aggregate F1 SoT).
_STAGE1_LOG_PATTERN = re.compile(
    r"Stage 1 호출 성공 — posting_id=\d+ 입력 토큰=(\d+) 출력 토큰=(\d+) "
    r"캐시 읽기=(\d+) 캐시 쓰기=(\d+)"
)

_logger = logging.getLogger(__name__)


@dataclass
class TokenStats:
    input_total: int = 0
    output_total: int = 0
    cache_read_total: int = 0
    cache_creation_total: int = 0
    call_count: int = 0


class TokenCaptureHandler(logging.Handler):
    """Stage 1 token usage log capture — F1 cache hit ratio aggregate."""

    def __init__(self, stats: TokenStats) -> None:
        super().__init__()
        self._stats = stats

    def emit(self, record: logging.LogRecord) -> None:
        match = _STAGE1_LOG_PATTERN.search(record.getMessage())
        if match is None:
            return
        self._stats.input_total += int(match.group(1))
        self._stats.output_total += int(match.group(2))
        self._stats.cache_read_total += int(match.group(3))
        self._stats.cache_creation_total += int(match.group(4))
        self._stats.call_count += 1


def _empty_int_list() -> list[int]:
    """`field(default_factory=...)` 양식 통일용 typed factory — pyright strict 안 list[Unknown] 회피 (`schemas.py` 양식 mirror)."""
    return []


@dataclass
class Metrics:
    total: int = 0
    auto_approved: int = 0
    needs_review: int = 0
    invalid_tag_count: int = 0
    total_tag_emit: int = 0
    low_conf_per_posting: list[int] = field(default_factory=_empty_int_list)
    child_path_emit: int = 0
    umbrella_only_postings: int = 0
    audit_row_count: int = 0
    fow_row_count: int = 0


async def _extract_one(
    session_factory: async_sessionmaker[AsyncSession],
    posting_id: int,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore, session_factory() as session:
        try:
            posting = await session.get(Posting, posting_id)
            if posting is None:
                _logger.warning("posting_id=%d 미존재 — 건너뜀", posting_id)
                return
            await reset_posting_for_re_extraction(session, posting)
            att_rows = await session.execute(
                sa.select(Attachment)
                .where(Attachment.posting_id == posting_id)
                .order_by(Attachment.id)
            )
            attachments = list(att_rows.scalars().all())
            await extract_posting(session, posting, attachments)
        except Exception:  # noqa: BLE001 — reset/fetch/LLM/DB 실패 demote to warning, gather isolation (CodeRabbit #3178194335)
            _logger.exception("extract_one 실패 — posting_id=%d", posting_id)


async def _collect_metrics(
    session_factory: async_sessionmaker[AsyncSession], posting_ids: Sequence[int]
) -> Metrics:
    metrics = Metrics(total=len(posting_ids))
    async with session_factory() as session:
        rows = await session.execute(sa.select(Posting).where(Posting.id.in_(posting_ids)))
        for posting in rows.scalars():
            data: dict[str, Any] | None = posting.extracted_data
            if data is None:
                continue
            if posting.needs_review:
                metrics.needs_review += 1
            else:
                metrics.auto_approved += 1
            tag_ids = list(data.get("field_of_work_tag_ids") or [])
            metrics.total_tag_emit += len(tag_ids)
            child_count = sum(1 for t in tag_ids if str(t).count(".") >= 2)
            metrics.child_path_emit += child_count
            if tag_ids and child_count == 0:
                metrics.umbrella_only_postings += 1
            confs: dict[str, Any] = data.get("field_confidence_scores") or {}
            low = sum(
                1 for v in confs.values() if isinstance(v, int | float) and v < _LOW_CONF_THRESHOLD
            )
            metrics.low_conf_per_posting.append(low)

        invalid = await session.execute(
            sa.select(sa.func.count())
            .select_from(ExtractionAuditLog)
            .where(
                ExtractionAuditLog.action == "STAGE2_INVALID_TAG",
                ExtractionAuditLog.posting_id.in_(posting_ids),
            )
        )
        metrics.invalid_tag_count = invalid.scalar() or 0

        audit_total = await session.execute(
            sa.select(sa.func.count()).select_from(ExtractionAuditLog)
        )
        metrics.audit_row_count = audit_total.scalar() or 0
        fow_total = await session.execute(
            sa.select(sa.func.count()).select_from(posting_fields_of_work)
        )
        metrics.fow_row_count = fow_total.scalar() or 0

    return metrics


def _format_baseline(
    metrics: Metrics, tokens: TokenStats, started_at: datetime, finished_at: datetime
) -> str:
    elapsed = (finished_at - started_at).total_seconds()
    auto_pct = 100 * metrics.auto_approved / metrics.total if metrics.total else 0.0
    invalid_pct = (
        100 * metrics.invalid_tag_count / metrics.total_tag_emit if metrics.total_tag_emit else 0.0
    )
    avg_low = (
        sum(metrics.low_conf_per_posting) / len(metrics.low_conf_per_posting)
        if metrics.low_conf_per_posting
        else 0.0
    )
    cache_total = tokens.cache_read_total + tokens.cache_creation_total
    hit_ratio = 100 * tokens.cache_read_total / cache_total if cache_total else 0.0
    child_emit_pct = (
        100 * metrics.child_path_emit / metrics.total_tag_emit if metrics.total_tag_emit else 0.0
    )
    umbrella_pct = 100 * metrics.umbrella_only_postings / metrics.total if metrics.total else 0.0
    pass_auto = "✓" if auto_pct >= 70 else "✗"
    pass_invalid = "✓" if invalid_pct < 5 else "✗"
    pass_lowconf = "✓" if avg_low < 2 else "✗"

    return f"""# M4 baseline (n={metrics.total} bizinfo postings)

> 실행: {started_at.isoformat()} → {finished_at.isoformat()} ({elapsed:.1f}s)
> SoT: M4.4 commit 3 `scripts/batch_baseline.py` (n={metrics.total}, source=bizinfo 단일).
> M4.4 머지 시점 통과 확정 = `docs/PROMPTS.md §7 line 413 + §5 line 386` SoT reversal 후속 갱신 (별 docs PR).

## Checkpoint 지표 (`docs/ARCHITECTURE.md §9 line 404-407` SoT)

| 지표 | 측정값 | 임계 | 통과 |
|------|--------|------|------|
| 자동승인 % | {auto_pct:.1f}% ({metrics.auto_approved}/{metrics.total}) | ≥ 70% | {pass_auto} |
| Invalid tag % | {invalid_pct:.2f}% ({metrics.invalid_tag_count}/{metrics.total_tag_emit}) | < 5% | {pass_invalid} |
| Low-conf 평균 | {avg_low:.2f}개/공고 | < 2개 | {pass_lowconf} |

## 분류 정확도 분포

- 자식 path 선택률: {child_emit_pct:.1f}% ({metrics.child_path_emit}/{metrics.total_tag_emit})
- Umbrella-only posting 비율: {umbrella_pct:.1f}% ({metrics.umbrella_only_postings}/{metrics.total})

## Cache hit ratio (F1 실측)

| 항목 | 값 |
|------|---|
| 호출 수 | {tokens.call_count} |
| 입력 토큰 (regular) | {tokens.input_total:,} |
| 출력 토큰 | {tokens.output_total:,} |
| Cache read 토큰 | {tokens.cache_read_total:,} |
| Cache creation 토큰 | {tokens.cache_creation_total:,} |
| **Hit ratio** | **{hit_ratio:.1f}%** |

## Row count snapshot (F7)

| 테이블 | row count (전체 DB) |
|--------|-------|
| `extraction_audit_logs` | {metrics.audit_row_count:,} |
| `posting_fields_of_work` | {metrics.fow_row_count:,} |

baseline_v2 (M4.4 commit 5 re-measurement) 측정 시 `_force_re_extract` DELETE 후 v1 결과 보존 X — 본 표 의 row count + 위 지표 가 trace SoT.

## 분포

| 항목 | 값 |
|------|---|
| Source | bizinfo (단일) |
| Sample size | n={metrics.total} |
| Total tag emit | {metrics.total_tag_emit} |
| Auto-approved | {metrics.auto_approved} |
| Needs review | {metrics.needs_review} |
"""


async def _run() -> int:
    configure_logging()
    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    tokens = TokenStats()
    capture = TokenCaptureHandler(tokens)
    stage1_logger = logging.getLogger("stepg_core.features.extraction.stage1")
    stage1_logger.addHandler(capture)
    stage1_logger.setLevel(logging.INFO)

    started_at = datetime.now(UTC)
    try:
        async with session_factory() as session:
            rows = await session.execute(
                sa.select(Posting.id).where(Posting.source == _TARGET_SOURCE).order_by(Posting.id)
            )
            posting_ids = list(rows.scalars().all())
        _logger.info("baseline 시작 — n=%d (source=%s)", len(posting_ids), _TARGET_SOURCE)

        if not posting_ids:
            _logger.warning("postings 부재 — 건너뜀")
            return 0

        semaphore = asyncio.Semaphore(_CONCURRENCY)
        await asyncio.gather(
            *(_extract_one(session_factory, pid, semaphore) for pid in posting_ids)
        )

        metrics = await _collect_metrics(session_factory, posting_ids)
        finished_at = datetime.now(UTC)
        content = _format_baseline(metrics, tokens, started_at, finished_at)
        _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT_PATH.write_text(content, encoding="utf-8")
        _logger.info(
            "baseline 적재 → %s (n=%d, %.1fs)",
            _OUTPUT_PATH,
            metrics.total,
            (finished_at - started_at).total_seconds(),
        )
    finally:
        stage1_logger.removeHandler(capture)
        await engine.dispose()
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
