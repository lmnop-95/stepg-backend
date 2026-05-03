"""Stage 1+2+3 orchestrator + DB persistence — `plan.md commit 7` SoT.

`extract_posting()` 단일 transaction 안:

(a) Stage 1 LLM 호출 (`stage1.call_stage1`)
(b) Stage 2 검증 + alias remap + invalid 로깅 (`stage2.validate_stage1_output`)
(c) Stage 3 신뢰도 분기 (`stage3.evaluate_stage3`)
(d) `Posting.{eligibility, extracted_data, summary, target_description, support_description,
   needs_review}` dual-write (eligibility 별 컬럼 + extracted_data 풀 dump 동시)
(e) `posting_fields_of_work` association DELETE-old + INSERT-new (Stage 2 valid_tag_ids)
(f) needs_review 분기 시 `ReviewQueueItem` insert; auto-approve 분기 시 `AUTO_APPROVE`
   audit row 적재 (Stage 2 invalid rows + 동시 commit)

**dual-write invariant** (`plan.md commit 7` SoT): M4 적재 + M9 편집 모두 4 컬럼 ↔
`extracted_data` 안 동일 4 키 동시 갱신. partial write = M6 Hard Filter / M9 audit
log mismatch.

Idempotency: `Posting.extracted_data IS NOT NULL` skip — M3 `parse_status` terminal
패턴 mirror. 재추출은 M9 admin 수동 트리거 (또는 Phase 1.5 의 M2 hash-mismatch
clear 후속).

Per-posting transaction: `extract_postings_batch` 가 각 posting 마다 새 session
+ commit. 한 posting 의 LLM/DB 실패가 batch 전체를 rollback 하지 않음 (M2/M3
pattern 일관, ingest_postings cron 안정성).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy_utils.primitives.ltree import Ltree
from stepg_core.features.extraction.stage1 import call_stage1
from stepg_core.features.extraction.stage2 import (
    AUDIT_INVALID_FIELD,
    AUDIT_INVALID_TAG,
    validate_stage1_output,
)
from stepg_core.features.extraction.stage3 import evaluate_stage3
from stepg_core.features.fields_of_work.models import FieldOfWork
from stepg_core.features.postings.models import (
    Attachment,
    Posting,
    posting_fields_of_work,
)
from stepg_core.features.review.models import ExtractionAuditLog, ReviewQueueItem

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# `features/review/models.py::AUDIT_ACTIONS` SoT mirror — M1 schema + 마이그레이션
# 0013 박힘. M9 큐레이터 행위 (`MANUAL_APPROVE` / `EDIT` / `REJECT`) 는 M9 PR scope.
_AUDIT_AUTO_APPROVE = "AUTO_APPROVE"


@dataclass(frozen=True)
class ExtractionResult:
    """Single-posting outcome — `extract_postings_batch` 의 카운터 입력."""

    posting_id: int
    skipped_idempotent: bool
    needs_review: bool
    invalid_tag_count: int
    invalid_field_count: int


@dataclass(frozen=True)
class ExtractionBatchResult:
    """Batch summary — `ingest_postings` cron 로그 (M2 `ParseResult` 패턴)."""

    extracted: int
    skipped_idempotent: int
    needs_review: int
    auto_approved: int
    failed: int


def _capture_pre_state(posting: Posting) -> dict[str, Any]:
    """`AUTO_APPROVE` audit row의 `before` snapshot — pre-extraction Posting 4 컬럼.

    M1 CHECK `(action = 'MANUAL_INSERT') = (before IS NULL)`로 AUTO_APPROVE 의 before
    NOT NULL 강제. 첫 추출 시점 보통 4 키 모두 null/empty — Posting 컬럼 mutation
    diff를 audit log 에 보존 (M9 admin 가 "Posting 었음 empty → full data" 직관
    파악).
    """
    return {
        "eligibility": posting.eligibility,
        "extracted_data": posting.extracted_data,
        "summary": posting.summary,
        "target_description": posting.target_description,
        "support_description": posting.support_description,
        "needs_review": posting.needs_review,
    }


async def _resolve_field_of_work_ids(
    session: AsyncSession,
    paths: list[str],
) -> list[Any]:
    """Stage 2 valid path 들 → `FieldOfWork.id` UUID 리스트.

    `posting_fields_of_work` association FK 적재용. taxonomy_cache 는 path 만 보유
    (메모리 상수), DB `FieldOfWork` row 의 UUID PK가 association 의 키.
    """
    if not paths:
        return []
    # `FieldOfWork.path` 는 `Mapped[Ltree]` (LtreeType) — `.in_(paths)` bind 시 각 str 을
    # `Ltree(str)` 로 cast 필요 (`fields_of_work/models.py` docstring SoT). golden 5
    # manual 실행에서 발견된 결함 (real-world bizinfo 데이터 첫 검증).
    rows = await session.execute(
        sa.select(FieldOfWork.id).where(FieldOfWork.path.in_([Ltree(p) for p in paths]))
    )
    return [row[0] for row in rows.all()]


async def extract_posting(
    session: AsyncSession,
    posting: Posting,
    attachments: list[Attachment],
) -> ExtractionResult:
    """Single-posting extraction — Stage 1+2+3 + DB persist atomic (`plan.md commit 7`).

    Idempotency: `Posting.extracted_data IS NOT NULL` 시 skip (M3 patten mirror).

    단일 transaction commit — Posting 4 컬럼 dual-write + association rebuild +
    ReviewQueueItem (분기 시) / AUTO_APPROVE audit (auto-approve 시) + Stage 2
    invalid rows 모두 한 번에 commit.
    """
    if posting.extracted_data is not None:
        return ExtractionResult(
            posting_id=posting.id,
            skipped_idempotent=True,
            needs_review=posting.needs_review,
            invalid_tag_count=0,
            invalid_field_count=0,
        )

    pre_state = _capture_pre_state(posting)

    raw = await call_stage1(posting, attachments)
    s2_result = validate_stage1_output(posting_id=posting.id, raw=raw)
    s3_decision = evaluate_stage3(s2_result)

    extracted = s2_result.extracted
    audit_rows: list[dict[str, Any]] = list(s2_result.audit_rows)

    # (d) Posting 컬럼 dual-write — `Posting.eligibility` 별 컬럼 + `extracted_data`
    # 풀 dump + 4 텍스트 컬럼 동시 갱신 (plan.md commit 7 dual-write invariant).
    posting.eligibility = extracted.eligibility.model_dump(mode="json")
    posting.extracted_data = extracted.model_dump(mode="json")
    posting.summary = extracted.summary
    posting.target_description = extracted.target_description
    posting.support_description = extracted.support_description
    posting.needs_review = s3_decision.needs_review

    # (e) posting_fields_of_work — DELETE-old + INSERT-new from Stage 2 valid paths.
    await session.execute(
        sa.delete(posting_fields_of_work).where(posting_fields_of_work.c.posting_id == posting.id)
    )
    fow_ids = await _resolve_field_of_work_ids(session, list(extracted.field_of_work_tag_ids))
    if fow_ids:
        await session.execute(
            posting_fields_of_work.insert(),
            [{"posting_id": posting.id, "field_of_work_id": fow_id} for fow_id in fow_ids],
        )

    # (f) Branch persist — needs_review 시 ReviewQueueItem (M9 큐레이터가 추후
    # MANUAL_APPROVE/REJECT audit emit), auto-approve 시 AUTO_APPROVE audit row.
    if s3_decision.needs_review:
        session.add(
            ReviewQueueItem(
                posting_id=posting.id,
                reasons=list(s3_decision.reasons),
                state="PENDING",
            )
        )
    else:
        audit_rows.append(
            {
                "posting_id": posting.id,
                "action": _AUDIT_AUTO_APPROVE,
                "before": pre_state,
                "after": extracted.model_dump(mode="json"),
                "actor_user_id": None,
            }
        )

    # ExtractionAuditLog rows (Stage 2 invalid + AUTO_APPROVE 통합 적재).
    if audit_rows:
        session.add_all(
            [
                ExtractionAuditLog(
                    posting_id=row["posting_id"],
                    action=row["action"],
                    before=row["before"],
                    after=row["after"],
                    actor_user_id=row["actor_user_id"],
                )
                for row in audit_rows
            ]
        )

    await session.commit()

    invalid_tag_count = sum(1 for r in audit_rows if r["action"] == AUDIT_INVALID_TAG)
    invalid_field_count = sum(1 for r in audit_rows if r["action"] == AUDIT_INVALID_FIELD)

    logger.info(
        "Stage 1-3 ok — posting_id=%d needs_review=%s invalid_tag=%d invalid_field=%d valid_tags=%d",
        posting.id,
        s3_decision.needs_review,
        invalid_tag_count,
        invalid_field_count,
        len(extracted.field_of_work_tag_ids),
    )

    return ExtractionResult(
        posting_id=posting.id,
        skipped_idempotent=False,
        needs_review=s3_decision.needs_review,
        invalid_tag_count=invalid_tag_count,
        invalid_field_count=invalid_field_count,
    )


async def extract_postings_batch(
    session_factory: async_sessionmaker[AsyncSession],
    posting_ids: list[int],
) -> ExtractionBatchResult:
    """Batch entry — `ingest_postings` cron의 5번째 stage.

    각 posting 마다 새 session으로 isolation — LLM 호출 / DB 실패가 batch 전체를
    abort 하지 않음 (M2/M3 per-attachment 실패 demote-to-warning 패턴 일관).
    """
    if not posting_ids:
        return ExtractionBatchResult(0, 0, 0, 0, 0)

    extracted = 0
    skipped_idempotent = 0
    needs_review = 0
    auto_approved = 0
    failed = 0

    for posting_id in posting_ids:
        try:
            async with session_factory() as session:
                posting = await session.get(Posting, posting_id)
                if posting is None:
                    logger.warning("posting_id=%d not found — extract skip", posting_id)
                    failed += 1
                    continue
                att_rows = await session.execute(
                    sa.select(Attachment)
                    .where(Attachment.posting_id == posting_id)
                    .order_by(Attachment.id)
                )
                attachments = list(att_rows.scalars().all())
                result = await extract_posting(session, posting, attachments)
        except Exception:  # noqa: BLE001 — 모든 LLM/DB 실패 demote to warning
            logger.exception("extract_posting 실패 — posting_id=%d", posting_id)
            failed += 1
            continue

        if result.skipped_idempotent:
            skipped_idempotent += 1
        else:
            extracted += 1
            if result.needs_review:
                needs_review += 1
            else:
                auto_approved += 1

    return ExtractionBatchResult(
        extracted=extracted,
        skipped_idempotent=skipped_idempotent,
        needs_review=needs_review,
        auto_approved=auto_approved,
        failed=failed,
    )


__all__ = [
    "ExtractionBatchResult",
    "ExtractionResult",
    "extract_posting",
    "extract_postings_batch",
]
