"""Ingestion pipeline orchestrator — fetch + persist + attachment download.

`ingest_postings` is the ARQ entry point registered in WorkerSettings.functions.
commit 3 wired fetch(모든 SOURCES) → persist; commit 5 adds attachment
download + LocalFsBackend wire. cron schedule lands in commit 6.

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

Attachment policy (Batch J):
- Streaming SHA-256 (8 KB chunks via `stream_to_temp_with_retry`) writes the
  body to a temp file under `storage_root/attachments` so `Path.replace` is
  same-FS atomic when handing off to `LocalFsBackend.put_path`.
- Per-download budget: `asyncio.timeout(60.0)` (Q87, ASYNC109 forbids the
  `timeout=` kwarg). Single-attachment failures are demoted to warnings; the
  rest of the batch proceeds (Q93, legacy B3).
- `Attachment` rows are inserted unconditionally — the same `content_hash`
  appearing under different `posting_id`s is a legitimate dedup signal that
  the FS layer already collapses.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import mimetypes
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from stepg_core.core.config import get_settings
from stepg_core.core.db import get_session_factory
from stepg_core.core.errors import HttpFetchError
from stepg_core.core.http import DEFAULT_TIMEOUT_SECONDS, stream_to_temp_with_retry
from stepg_core.core.storage import LocalFsBackend
from stepg_core.features.ingestion.sources.registry import SOURCES
from stepg_core.features.postings.models import Attachment, Posting

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession
    from stepg_core.core.storage import StorageBackend
    from stepg_core.features.ingestion.schemas import RawPostingPayload

# bizinfo attachments are ~95% .hwp / .hwpx. The stdlib mimetypes DB has no
# entry for these on macOS Python 3.14; without these registrations every row
# would fall through to `application/octet-stream` and the `Attachment.mime`
# column would lose diagnostic value (Pass 8-I). Module-level side effect on
# import is intentional — single source of truth, no caller setup required.
mimetypes.add_type("application/x-hwp", ".hwp")
mimetypes.add_type("application/x-hwpx", ".hwpx")

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


# Outer caller hard-cap (Pass 8-F): intentionally equal to
# `core/http.py::_STOP_AFTER_DELAY_SECONDS` (60 s). The internal tenacity
# `stop_after_delay` ends retry attempts; this `asyncio.timeout` guards
# against any caller-side wedging beyond that budget. Phase 1 simplification —
# split the two values only when retry waits become non-trivial.
_ATTACHMENT_DOWNLOAD_TIMEOUT_SECONDS = 60.0


async def download_attachments(
    session: AsyncSession,
    payloads: list[RawPostingPayload],
    *,
    client: httpx.AsyncClient,
    backend: StorageBackend,
    into_dir: Path,
) -> int:
    """Download every `RawPostingPayload.attachments` ref + insert Attachment rows.

    Resolves `posting_id` per payload via a single `SELECT … WHERE (source,
    source_id) IN (…)` keyed on the `uq_postings_source_dedup` index — avoids
    threading IDs through `persist_postings`'s return shape just for this
    follow-up step. Each attachment is streamed into a temp file under
    `into_dir` (same FS as `backend` for atomic `Path.replace`), hashed, then
    handed to `backend.put_path` which collapses duplicates by hash.

    DB dedup (Pass 8-A): inserts use
    `pg_insert(Attachment).on_conflict_do_nothing` against
    `uq_attachments_posting_content` (migration 0010) so cron re-runs do not
    grow the table. The `saved` counter reflects rows attempted (not
    physically INSERTed after conflict skip) — fine for monitoring but not
    an authoritative growth metric.

    Per-attachment failures (HTTP retry exhaustion or 60 s timeout) are
    demoted to warnings (Q93); the rest of the batch proceeds. All rows are
    committed in a **single transaction at end** — DB-level failure rolls
    back the entire batch (FS files remain on disk and dedup on next cron
    via `LocalFsBackend.exists`).

    `put_path` failure leaks the source temp file (Pass 8-M); operate
    `find {storage_root}/attachments -name 'attach-*' -mtime +1 -delete` as
    cleanup until Phase 1.5 hardens this with try/finally.
    """
    if not payloads:
        return 0

    keys = {(p.source, p.source_id) for p in payloads if p.attachments}
    if not keys:
        return 0

    rows = await session.execute(
        sa.select(Posting.id, Posting.source, Posting.source_id).where(
            sa.tuple_(Posting.source, Posting.source_id).in_(keys)
        )
    )
    id_by_key: dict[tuple[str, str], int] = {(r.source, r.source_id): r.id for r in rows.all()}

    saved = 0
    rows_to_insert: list[dict[str, Any]] = []
    for payload in payloads:
        if not payload.attachments:
            continue
        posting_id = id_by_key.get((payload.source, payload.source_id))
        if posting_id is None:
            logger.warning(
                "posting_id 미매칭 — 첨부 skip (source=%s, source_id=%s)",
                payload.source,
                payload.source_id,
            )
            continue
        for ref in payload.attachments:
            try:
                async with asyncio.timeout(_ATTACHMENT_DOWNLOAD_TIMEOUT_SECONDS):
                    temp_path, content_hash, size = await stream_to_temp_with_retry(
                        client, ref.url, into_dir=into_dir
                    )
            except HttpFetchError, TimeoutError:
                logger.exception(
                    "attachment download 실패 — posting_id=%d filename=%s",
                    posting_id,
                    ref.filename,
                )
                continue
            stored_path = await backend.put_path(content_hash, temp_path)
            mime, _ = mimetypes.guess_type(ref.filename)
            rows_to_insert.append(
                {
                    "posting_id": posting_id,
                    "filename": ref.filename,
                    "mime": mime or "application/octet-stream",
                    "content_hash": content_hash,
                    "local_path": str(stored_path),
                }
            )
            saved += 1
            logger.info(
                "attachment saved — posting_id=%d filename=%s size=%d hash=%s",
                posting_id,
                ref.filename,
                size,
                content_hash[:12],
            )

    if rows_to_insert:
        stmt = (
            pg_insert(Attachment)
            .values(rows_to_insert)
            .on_conflict_do_nothing(index_elements=["posting_id", "content_hash"])
        )
        await session.execute(stmt)
    await session.commit()
    return saved


async def ingest_postings(ctx: dict[str, Any]) -> None:  # noqa: ARG001 — ARQ ctx 시그니처 고정
    """ARQ entry point — fetch all sources, persist postings, download attachments.

    commit 3 wired fetch + persist; commit 5 adds attachment download +
    `LocalFsBackend` instantiation. cron schedule is commit 6.
    """
    settings = get_settings()
    # `into_dir == backend root subtree` — `Path.replace` atomic on same FS
    # (Pass 8-K). Phase 1.5 R2/S3 backend will need `backend.tempdir()` API
    # to keep this invariant when temp lives on local FS but dst lives remote.
    attachments_root = settings.storage_root / "attachments"
    attachments_root.mkdir(parents=True, exist_ok=True)
    backend: StorageBackend = LocalFsBackend(attachments_root)

    now = datetime.now(UTC)
    totals = PersistResult(received=0, inserted=0, updated=0)
    saved_total = 0
    factory = get_session_factory()
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=True
    ) as attach_client:
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
            async with factory() as session:
                saved = await download_attachments(
                    session,
                    payloads,
                    client=attach_client,
                    backend=backend,
                    into_dir=attachments_root,
                )
            logger.info(
                "ingest source=%s received=%d inserted=%d updated=%d attachments_attempted=%d",
                source,
                result.received,
                result.inserted,
                result.updated,
                saved,
            )
            totals = replace(
                totals,
                received=totals.received + result.received,
                inserted=totals.inserted + result.inserted,
                updated=totals.updated + result.updated,
            )
            saved_total += saved
    logger.info(
        "ingest_postings done — received=%d inserted=%d updated=%d attachments_attempted=%d",
        totals.received,
        totals.inserted,
        totals.updated,
        saved_total,
    )


__all__ = [
    "PersistResult",
    "download_attachments",
    "ingest_postings",
    "persist_postings",
]
