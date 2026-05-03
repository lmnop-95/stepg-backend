"""Golden 5 케이스 — `docs/PROMPTS.md §8` real Anthropic API spot check.

5 케이스 (분야 3 + 난이도 2):
- §8.1 AI (easy) — bizinfo `PBLN_000000000121189` (제조 암묵지 AI 모델 R&D)
- §8.2 제조·소재 cleantech (medium) — bizinfo `PBLN_000000000121184` (전남 탄소중립 제조혁신)
- §8.3 콘텐츠 수출 (medium) — bizinfo `PBLN_000000000121252` (싱가포르 K-콘텐츠 IP)
- §8.4 invalid trigger (hard, 합성) — 양자컴퓨팅 본문 → `tech.quantum.computing` 환각
- §8.5 모호 multi-tag (hard, 합성) — AI 의료 진단 SaaS 본문 → digital_health + ai_ml.cv

채점 (`PROMPTS.md §8` 첫 단락 임계 일관):
- 자동: tag set Jaccard ≥ 0.75 (multi-tag 부분 일치) + single-value 정확 일치 + Stage
  2/3 분기 outcome.
- 큐레이터: summary 자연 reading + boundary 룰 적용 일관성 (manual visual review).

본 테스트는 `pytest --run-golden` opt-in 시만 실행 — `conftest.py` SoT 참조.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
import sqlalchemy as sa
from stepg_core.features.extraction.service import extract_posting
from stepg_core.features.postings.models import Attachment, Posting
from stepg_core.features.review.models import ExtractionAuditLog

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.golden


# ============================================================================
# Helpers
# ============================================================================


async def _fetch_bizinfo_posting(session: AsyncSession, source_id: str) -> Posting | None:
    """bizinfo source_id 로 Posting fetch — 미존재 시 None (test skip 신호)."""
    rows = await session.execute(
        sa.select(Posting).where(Posting.source == "bizinfo", Posting.source_id == source_id)
    )
    return rows.scalar_one_or_none()


async def _fetch_attachments(session: AsyncSession, posting_id: int) -> list[Attachment]:
    """Posting attachments fetch — `extract_posting` signature 정합 (id ascending)."""
    rows = await session.execute(
        sa.select(Attachment).where(Attachment.posting_id == posting_id).order_by(Attachment.id)
    )
    return list(rows.scalars().all())


async def _force_re_extract(session: AsyncSession, posting: Posting) -> None:
    """Idempotency check (`extracted_data IS NOT NULL` skip) 우회 — 본 테스트가
    재추출을 강제하기 위해 미리 Posting 의 extracted_data / eligibility 컬럼 reset.
    """
    posting.extracted_data = None
    posting.eligibility = None
    posting.summary = ""
    posting.target_description = ""
    posting.support_description = ""
    posting.needs_review = False
    await session.commit()


def _jaccard(a: set[str], b: set[str]) -> float:
    """Tag set Jaccard similarity (`PROMPTS.md §8` 채점 임계 입력)."""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


# ============================================================================
# Bizinfo 3 cases — DB lookup + skip-if-missing
# ============================================================================


async def test_golden_8_1_ai_easy(db_session: AsyncSession) -> None:
    """`PROMPTS.md §8.1` — AI (easy) — `PBLN_000000000121189`.

    expected:
    - tags: tech.ai_ml.* 자식 1+ (generative / mlops 등) + tech.manufacturing.smart_factory
      cross-tag + biz.b2b_saas.dev_tools (multi-tag dense)
    - corporate_types_allowed: ["중소기업"]
    - funding_uses: ["R&D"]
    """
    posting = await _fetch_bizinfo_posting(db_session, "PBLN_000000000121189")
    if posting is None:
        pytest.skip("bizinfo PBLN_000000000121189 미적재 — M2 cron 실행 필요")

    await _force_re_extract(db_session, posting)
    attachments = await _fetch_attachments(db_session, posting.id)
    await extract_posting(db_session, posting, attachments)

    await db_session.refresh(posting)
    extracted_data = posting.extracted_data or {}
    eligibility = posting.eligibility or {}
    actual_tags = set(extracted_data.get("field_of_work_tag_ids") or [])

    expected_tags = {
        "tech.ai_ml.generative",
        "tech.ai_ml.mlops",
        "tech.manufacturing.smart_factory",
        "biz.b2b_saas.dev_tools",
    }
    jaccard = _jaccard(expected_tags, actual_tags)
    assert jaccard >= 0.75, (
        f"§8.1 tag Jaccard {jaccard:.2f} < 0.75 — expected ⊃ {expected_tags & actual_tags}, "
        f"actual {actual_tags}"
    )
    assert eligibility.get("corporate_types_allowed") == ["중소기업"], (
        f"§8.1 corporate_types_allowed {eligibility.get('corporate_types_allowed')!r} ≠ ['중소기업']"
    )
    assert extracted_data.get("funding_uses") == ["R&D"], (
        f"§8.1 funding_uses {extracted_data.get('funding_uses')!r} ≠ ['R&D']"
    )


async def test_golden_8_2_cleantech_medium(db_session: AsyncSession) -> None:
    """`PROMPTS.md §8.2` — 제조·소재 cleantech (medium) — `PBLN_000000000121184`.

    expected (auto, PROMPTS.md §8.2 line 453 채점 임계):
    - tags: tech.cleantech.* 1+ + tech.manufacturing.process cross-tag (§5.1 (a) boundary)
    - location_required_sido: ["전라남도"]

    expected (큐레이터 visual review, 채점 임계 외부):
    - corporate_types_allowed: ["중소기업"]
    - funding_uses: ["R&D", "시설투자"]
    """
    posting = await _fetch_bizinfo_posting(db_session, "PBLN_000000000121184")
    if posting is None:
        pytest.skip("bizinfo PBLN_000000000121184 미적재 — M2 cron 실행 필요")

    await _force_re_extract(db_session, posting)
    attachments = await _fetch_attachments(db_session, posting.id)
    await extract_posting(db_session, posting, attachments)

    await db_session.refresh(posting)
    extracted_data = posting.extracted_data or {}
    eligibility = posting.eligibility or {}
    actual_tags = set(extracted_data.get("field_of_work_tag_ids") or [])

    cleantech_paths = {p for p in actual_tags if p.startswith("tech.cleantech.")}
    manufacturing_paths = {p for p in actual_tags if p.startswith("tech.manufacturing.")}
    assert cleantech_paths, f"§8.2 cleantech path 적어도 1개 — actual {actual_tags}"
    assert manufacturing_paths, (
        f"§8.2 manufacturing cross-tag 적어도 1개 (§5.1 (a) boundary) — actual {actual_tags}"
    )
    assert eligibility.get("location_required_sido") == ["전라남도"], (
        f"§8.2 location_required_sido {eligibility.get('location_required_sido')!r} ≠ ['전라남도']"
    )


async def test_golden_8_3_content_export_medium(db_session: AsyncSession) -> None:
    """`PROMPTS.md §8.3` — 콘텐츠 수출 (medium) — `PBLN_000000000121252`.

    expected:
    - tags: biz.content_media umbrella 또는 자식 (video/music/webtoon) 적어도 2개
    - funding_uses: ["수출"]
    - location_required_sido: ["전국"]
    """
    posting = await _fetch_bizinfo_posting(db_session, "PBLN_000000000121252")
    if posting is None:
        pytest.skip("bizinfo PBLN_000000000121252 미적재 — M2 cron 실행 필요")

    await _force_re_extract(db_session, posting)
    attachments = await _fetch_attachments(db_session, posting.id)
    await extract_posting(db_session, posting, attachments)

    await db_session.refresh(posting)
    extracted_data = posting.extracted_data or {}
    eligibility = posting.eligibility or {}
    actual_tags = set(extracted_data.get("field_of_work_tag_ids") or [])

    content_media_paths = {p for p in actual_tags if p.startswith("biz.content_media")}
    assert len(content_media_paths) >= 2, (
        f"§8.3 biz.content_media umbrella + 자식 적어도 2개 — actual {content_media_paths}"
    )
    assert extracted_data.get("funding_uses") == ["수출"], (
        f"§8.3 funding_uses {extracted_data.get('funding_uses')!r} ≠ ['수출']"
    )
    assert eligibility.get("location_required_sido") == ["전국"], (
        f"§8.3 location_required_sido {eligibility.get('location_required_sido')!r} ≠ ['전국']"
    )


# ============================================================================
# Synthetic 2 cases — Posting fixture (insert + cleanup)
# ============================================================================


@pytest_asyncio.fixture
async def synthetic_invalid_trigger(db_session: AsyncSession) -> AsyncIterator[Posting]:
    """§8.4 합성 — 양자컴퓨팅 R&D 본문. LLM 환각 → `tech.quantum.computing` invalid drop 유도."""
    body = (
        "지원사업: 2026년 양자컴퓨팅·양자통신 R&D 지원 사업\n\n"
        "지원대상: 중소기업\n\n"
        "지원내용: 양자컴퓨팅 기반 알고리즘 개발 + 양자통신 인프라 구축 + 양자센서 응용\n"
        "R&D 자금 최대 5억원\n\n"
        "신청기간: 2026-06-30 까지\n\n"
        "신청자격: 중소기업기본법 상 중소기업"
    )
    posting = Posting(
        source="bizinfo",
        source_id="GOLDEN_8_4_QUANTUM_SYNTHETIC",
        title="2026년 양자컴퓨팅·양자통신 R&D 지원 사업 (synthetic)",
        deadline_at=None,
        status="ACTIVE",
        eligibility=None,
        extracted_data=None,
        raw_payload={
            "bsnsSumryCn": body,
            "jrsdInsttNm": "synthetic-test-부처",
            "reqstBeginEndDe": "2026-06-30 까지",
        },
        summary="",
        target_description="",
        support_description="",
        content_hash="synthetic-golden-8-4-quantum",
        needs_review=False,
    )
    db_session.add(posting)
    await db_session.commit()
    yield posting
    await db_session.delete(posting)
    await db_session.commit()


@pytest_asyncio.fixture
async def synthetic_ambiguous_multi_tag(db_session: AsyncSession) -> AsyncIterator[Posting]:
    """§8.5 합성 — AI 의료 진단 SaaS + 클리닉 운영. boundary 룰 + fabricate guard 검증."""
    body = (
        "지원사업: AI 기반 의료 진단 SaaS 개발 지원 사업\n\n"
        "지원대상: 중소기업\n\n"
        "지원내용: AI 모델 개발 (의료 영상 진단) + SaaS 플랫폼 구축 + 클리닉 운영\n"
        "효율화 도구 개발 R&D 자금 지원\n\n"
        "신청기간: 2026-08-31 까지\n\n"
        "신청자격: 중소기업기본법 상 중소기업"
    )
    posting = Posting(
        source="bizinfo",
        source_id="GOLDEN_8_5_AI_MED_SYNTHETIC",
        title="AI 기반 의료 진단 SaaS 개발 지원 사업 (synthetic)",
        deadline_at=None,
        status="ACTIVE",
        eligibility=None,
        extracted_data=None,
        raw_payload={
            "bsnsSumryCn": body,
            "jrsdInsttNm": "synthetic-test-부처",
            "reqstBeginEndDe": "2026-08-31 까지",
        },
        summary="",
        target_description="",
        support_description="",
        content_hash="synthetic-golden-8-5-ai-med",
        needs_review=False,
    )
    db_session.add(posting)
    await db_session.commit()
    yield posting
    await db_session.delete(posting)
    await db_session.commit()


async def test_golden_8_4_invalid_trigger(
    db_session: AsyncSession,
    synthetic_invalid_trigger: Posting,
) -> None:
    """`PROMPTS.md §8.4` — invalid trigger (hard) — 양자컴퓨팅 환각.

    expected (LLM 환각 시나리오):
    - LLM Stage 1 출력 → `tech.quantum.computing` (트리 부재 path)
    - Stage 2 alias-remap (a)/(b) 모두 miss → invalid drop
    - `STAGE2_INVALID_TAG` audit row 적재 (≥ 1)
    - Stage 2 final `field_of_work_tag_ids` = [] (빈 배열)
    - Stage 3 분기: 조건 1 (invalid ≥ 1) AND 조건 4 (valid 0) 동시 trigger → needs_review

    채점:
    - audit_log row count ≥ 1 (`STAGE2_INVALID_TAG`)
    - field_of_work_tag_ids = []
    - needs_review = True
    """
    posting = synthetic_invalid_trigger
    attachments = await _fetch_attachments(db_session, posting.id)
    await extract_posting(db_session, posting, attachments)

    await db_session.refresh(posting)
    extracted_data = posting.extracted_data or {}
    actual_tags = set(extracted_data.get("field_of_work_tag_ids") or [])

    audit_rows = (
        (
            await db_session.execute(
                sa.select(ExtractionAuditLog).where(
                    ExtractionAuditLog.posting_id == posting.id,
                    ExtractionAuditLog.action == "STAGE2_INVALID_TAG",
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(audit_rows) >= 1, (
        f"§8.4 STAGE2_INVALID_TAG audit row 적어도 1건 — actual count={len(audit_rows)}"
    )
    assert not actual_tags, f"§8.4 final field_of_work_tag_ids 빈 배열 — actual {actual_tags}"
    assert posting.needs_review is True, (
        f"§8.4 needs_review True (invalid ≥1 + valid 0) — actual {posting.needs_review}"
    )


async def test_golden_8_5_ambiguous_multi_tag(
    db_session: AsyncSession,
    synthetic_ambiguous_multi_tag: Posting,
) -> None:
    """`PROMPTS.md §8.5` — 모호 multi-tag (hard) — AI 의료 진단 SaaS.

    expected (auto, boundary 룰 §5.1 (a) + fabricate guard 검증):
    - tags: `tech.bio.digital_health` (SW 측면 우선) + `tech.ai_ml.cv` 또는
      `tech.ai_ml` umbrella (AI 의료 진단 = 영상 인식)
    - certifications_preferred: null (fabricate guard rail — 본문 외 도메인 prior 추측 차단)

    expected (큐레이터 visual review, 채점 임계 외부):
    - funding_uses: ["R&D"]

    채점:
    - tech.bio.digital_health 발견
    - tech.ai_ml umbrella 또는 자식 (cv 등) 적어도 1개 cross-tag
    - certifications_preferred = null
    """
    posting = synthetic_ambiguous_multi_tag
    attachments = await _fetch_attachments(db_session, posting.id)
    await extract_posting(db_session, posting, attachments)

    await db_session.refresh(posting)
    extracted_data = posting.extracted_data or {}
    eligibility = posting.eligibility or {}
    actual_tags = set(extracted_data.get("field_of_work_tag_ids") or [])

    assert "tech.bio.digital_health" in actual_tags, (
        f"§8.5 tech.bio.digital_health (SW 측면 우선, §5.1 (a) boundary) — actual {actual_tags}"
    )
    ai_ml_paths = {p for p in actual_tags if p == "tech.ai_ml" or p.startswith("tech.ai_ml.")}
    assert ai_ml_paths, (
        f"§8.5 tech.ai_ml umbrella 또는 자식 cross-tag 적어도 1개 — actual {actual_tags}"
    )
    assert eligibility.get("certifications_preferred") is None, (
        f"§8.5 certifications_preferred null (fabricate guard rail) — "
        f"actual {eligibility.get('certifications_preferred')!r}"
    )
