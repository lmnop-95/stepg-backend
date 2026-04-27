"""Ingestion pipeline orchestrator — fetch + persist (M2 commit 3).

`ingest_postings` is the ARQ entry point registered in WorkerSettings.functions.
commit 3 wires fetch(모든 SOURCES) → persist → count log. Attachment download
lands in commit 5/6.

Persist policy (`docs/.local/feat/ingestion/M2-bizinfo/plan.md` Batch H):
- Upsert on `(source, source_id)` (M1 `uq_postings_source_dedup`) → DO UPDATE
  unconditionally (Q27 — Q23 status is time-dependent: a row that was ACTIVE
  yesterday must transition to CLOSED today even if the source response is
  byte-identical). DO NOTHING leaves status stale; the IS DISTINCT FROM guard
  is rejected (Q63) for the same reason — content_hash excludes status by
  design (Q6) so the guard would skip the very rows that need a status flip.
- `now` is sampled once per persist call (Q66 batch consistency); status
  resolution and `updated_at` use the same instant.
- `_payload_hash` uses deterministic JSON (sort_keys + ensure_ascii=False +
  separators) so Pydantic version bumps cannot silently change the hash (Q48).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from stepg_core.core.db import get_session_factory
from stepg_core.core.errors import HttpFetchError
from stepg_core.features.ingestion.sources.registry import SOURCES
from stepg_core.features.postings.models import Posting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from stepg_core.features.ingestion.schemas import RawPostingPayload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersistResult:
    received: int
    inserted: int
    updated: int


def _resolve_status(
    apply_end_at: datetime | None, *, now: datetime
) -> Literal["ACTIVE", "CLOSED", "DRAFT"]:
    """Q23 status tree.

    `apply_end_at >= now` → ACTIVE / `< now` → CLOSED / None → DRAFT.
    `apply_start_at` is intentionally ignored — M6 Hard Filter only cares about
    deadline. EXPIRED is reserved for Phase 1.5 ops data; adding it here will
    naturally fail typecheck at every caller as a trace point.
    """
    if apply_end_at is None:
        return "DRAFT"
    return "ACTIVE" if apply_end_at >= now else "CLOSED"


def _payload_hash(payload: RawPostingPayload) -> str:
    """Deterministic SHA-256 hex of the normalized payload (Q48).

    `sort_keys=True` + `ensure_ascii=False` + `separators=(",", ":")` make the
    serialization byte-stable across Pydantic minor versions and Python builds,
    so `Posting.content_hash` only changes when source data actually changes.
    `mode="json"` so `datetime` becomes ISO-8601 strings (deterministic).
    """
    body = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _row_for_upsert(payload: RawPostingPayload, *, now: datetime) -> dict[str, Any]:
    # `created_at`/`updated_at`을 명시적으로 박아 INSERT path도 Python `now`로 통일
    # (Q66 batch consistency). 미명시 시 INSERT는 server_default `now()` (DB clock)로
    # fallback해 같은 batch 안에서 INSERT/UPDATE 시각이 분산됨.
    return {
        "source": payload.source,
        "source_id": payload.source_id,
        "title": payload.title,
        "deadline_at": payload.apply_end_at,
        "status": _resolve_status(payload.apply_end_at, now=now),
        "content_hash": _payload_hash(payload),
        "raw_payload": payload.raw_payload,
        "created_at": now,
        "updated_at": now,
    }


async def persist_postings(
    session: AsyncSession,
    payloads: list[RawPostingPayload],
    *,
    now: datetime,
) -> PersistResult:
    """Upsert payloads on `(source, source_id)` with unconditional DO UPDATE.

    Returns counts via Postgres `xmax` heuristic — `xmax=0` means INSERT,
    nonzero means UPDATE on this row's last touch (Postgres convention; works
    inside the same transaction because RETURNING reads the row state after
    the upsert applies).

    Commits the session before return — caller should not call `commit()`
    again on this session. Phase 1.5에 caller-managed transaction이 필요해지면
    그때 분리.
    """
    if not payloads:
        return PersistResult(received=0, inserted=0, updated=0)

    rows = [_row_for_upsert(p, now=now) for p in payloads]
    insert_stmt = pg_insert(Posting).values(rows)
    # `xmax = 0` after upsert ⇒ row was INSERTed, nonzero ⇒ UPDATEd (Postgres
    # convention; the column is system-generated so SQLAlchemy has no typed
    # entity for it — `literal_column` with explicit `BigInteger` keeps pyright
    # honest).
    xmax = sa.literal_column("xmax", type_=sa.BigInteger).label("xmax")
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["source", "source_id"],
        set_={
            "title": insert_stmt.excluded.title,
            "deadline_at": insert_stmt.excluded.deadline_at,
            "status": insert_stmt.excluded.status,
            "content_hash": insert_stmt.excluded.content_hash,
            "raw_payload": insert_stmt.excluded.raw_payload,
            "updated_at": now,
        },
    ).returning(Posting.id, xmax)

    result = await session.execute(upsert_stmt)
    inserted = 0
    updated = 0
    for row in result.all():
        if row.xmax == 0:
            inserted += 1
        else:
            updated += 1
    await session.commit()
    return PersistResult(received=len(payloads), inserted=inserted, updated=updated)


async def ingest_postings(_ctx: dict[str, Any]) -> None:
    """ARQ entry point — fetch all sources, persist, log counts.

    commit 3 covers fetch + persist. Attachment download is commit 5; cron
    schedule is commit 6.
    """
    now = datetime.now(UTC)
    totals = PersistResult(received=0, inserted=0, updated=0)
    factory = get_session_factory()
    for source, fetcher in SOURCES.items():
        try:
            payloads = await fetcher()
        except HttpFetchError, RuntimeError:
            # HttpFetchError: retry exhaustion (commit 1). RuntimeError:
            # `BIZINFO_API_KEY 미설정` (Q25) + bizinfo response 구조 drift
            # (`_extract_items`). 코드 버그류(TypeError/AttributeError/ImportError)는
            # propagate해서 ARQ 다음 cron이 재시도하거나 실패가 드러나도록 둠.
            logger.exception("ingest source 실패 — source=%s", source)
            continue
        async with factory() as session:
            result = await persist_postings(session, payloads, now=now)
        logger.info(
            "ingest source=%s received=%d inserted=%d updated=%d",
            source,
            result.received,
            result.inserted,
            result.updated,
        )
        totals = replace(
            totals,
            received=totals.received + result.received,
            inserted=totals.inserted + result.inserted,
            updated=totals.updated + result.updated,
        )
    logger.info(
        "ingest_postings done — received=%d inserted=%d updated=%d",
        totals.received,
        totals.inserted,
        totals.updated,
    )


__all__ = ["PersistResult", "ingest_postings", "persist_postings"]
