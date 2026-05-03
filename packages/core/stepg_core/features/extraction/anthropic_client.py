"""Anthropic SDK client wrapper + extract_posting_data tool schema.

M4 commit 3 — scaffolding for Stage 1 LLM 호출 (commit 4). Provides:

- `EXTRACT_POSTING_DATA_TOOL`: tool input_schema 상수. `docs/PROMPTS.md §1` +
  `§1.1` inline expand — Anthropic tool input_schema 가 `$ref`/`$defs` 미지원
  이라 18 `EligibilityRules` 필드를 §1 의 `eligibility` 자리에 직접 박음. §1
  또는 §1.1 갱신 시 본 상수 + Pydantic 모델 (commit 5 `schemas.py`) 동기 갱신
  필수 — `PROMPTS.md §0` mandate (cache invalidation 만으로 부족, runtime stale
  schema 가 LLM validation mismatch 유발).
- `get_anthropic_client()`: `@lru_cache(maxsize=1)` `AsyncAnthropic` 싱글톤
  (내부 connection pool 재사용 + project convention `get_settings`/`_load`
  동일 idiom). SDK default `max_retries=2` (HTTP 5xx / 429 자동 retry) +
  외층 `asyncio.timeout(60.0)` wrapper (commit 4 call site 책임) = CLAUDE.md
  absolute rule C (timeout + retry 강제) 만족.

Stage 1 actual call site (cache_control × 2, system/user prompt 주입,
tool_choice 강제, tool arguments 파싱) 은 commit 4 (`prompts.py` + `service.py`).
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, get_args

from anthropic import AsyncAnthropic
from stepg_core.core.config import get_settings
from stepg_core.features.extraction.schemas import (
    CertificationLiteral,
    FundingUseLiteral,
)

if TYPE_CHECKING:
    import logging

# 6종 인증 / 7종 funding_uses enum — `schemas.py` Pydantic Literal이 SoT, `get_args`로
# list 추출 (Pass 5 critic F3 dual SoT 회피). ARCHITECTURE.md §4.1 / §8.2 / §4.2 SoT
# 변경 시 `schemas.py`만 갱신 → 본 list 자동 동기.
_CERTIFICATION_ENUM: list[str] = list(get_args(CertificationLiteral))
_FUNDING_USES_ENUM: list[str] = list(get_args(FundingUseLiteral))

# PROMPTS.md §1.1 — EligibilityRules 18 필드 inline schema. 갱신 시: 필드명 / type
# / nullable / 6종 인증 enum / KSIC 양식 변경 = 본 dict + Pydantic
# `EligibilityRules` (commit 5 `schemas.py`) 동기 갱신.
_ELIGIBILITY_PROPERTIES: dict[str, dict[str, Any]] = {
    "corporate_types_allowed": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "허용 기업 형태 (예: '중소기업', '소상공인'). null = 무제한.",
    },
    "corporate_types_excluded": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "배제 기업 형태.",
    },
    "employee_count_min": {
        "type": ["integer", "null"],
        "description": "상시근로자 수 하한.",
    },
    "employee_count_max": {
        "type": ["integer", "null"],
        "description": "상시근로자 수 상한.",
    },
    "revenue_last_year_min": {
        "type": ["integer", "null"],
        "description": "전년도 연매출 하한 (원).",
    },
    "revenue_last_year_max": {
        "type": ["integer", "null"],
        "description": "전년도 연매출 상한 (원).",
    },
    "years_in_business_min": {
        "type": ["integer", "null"],
        "description": "사업 연차 하한.",
    },
    "years_in_business_max": {
        "type": ["integer", "null"],
        "description": "사업 연차 상한.",
    },
    "location_required_sido": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "필수 주소 시도 (광역명, '전국' 가능). null = 무제한.",
    },
    "location_preferred_sido": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "우대 가점 시도.",
    },
    "location_excluded_sido": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "배제 시도.",
    },
    "industry_ksic_allowed": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "허용 KSIC 코드 리스트 (숫자만, 대분류 알파벳 제외).",
    },
    "industry_ksic_excluded": {
        "type": ["array", "null"],
        "items": {"type": "string"},
        "description": "배제 KSIC 코드 리스트.",
    },
    "certifications_required": {
        "type": ["array", "null"],
        "items": {"type": "string", "enum": _CERTIFICATION_ENUM},
        "description": "필수 인증 (6종 enum).",
    },
    "certifications_preferred": {
        "type": ["array", "null"],
        "items": {"type": "string", "enum": _CERTIFICATION_ENUM},
        "description": "우대 인증.",
    },
    "certifications_excluded": {
        "type": ["array", "null"],
        "items": {"type": "string", "enum": _CERTIFICATION_ENUM},
        "description": "배제 인증.",
    },
    "prior_recipients_excluded": {
        "type": "boolean",
        "description": "기수혜자 배제 여부. 명시 없으면 false 로 emit 강제.",
    },
    "free_text_conditions": {
        "type": "array",
        "items": {"type": "string"},
        "description": "자동 처리 못한 조건 보존 (자유 텍스트). 잔여 없으면 빈 배열 emit 강제.",
    },
}
_ELIGIBILITY_REQUIRED: list[str] = [
    "corporate_types_allowed",
    "corporate_types_excluded",
    "employee_count_min",
    "employee_count_max",
    "revenue_last_year_min",
    "revenue_last_year_max",
    "years_in_business_min",
    "years_in_business_max",
    "location_required_sido",
    "location_preferred_sido",
    "location_excluded_sido",
    "industry_ksic_allowed",
    "industry_ksic_excluded",
    "certifications_required",
    "certifications_preferred",
    "certifications_excluded",
    "prior_recipients_excluded",
    "free_text_conditions",
]

# field_confidence_scores: eligibility 18 필드 1:1 strict (PROMPTS.md §1).
# additionalProperties: false 로 키 누락 / 추가 emit 모두 차단 → Stage 3 분기의
# low-conf eligibility 카운트 결정성 보장.
_FIELD_CONFIDENCE_PROPERTIES: dict[str, dict[str, Any]] = {
    name: {"type": "number", "minimum": 0, "maximum": 1} for name in _ELIGIBILITY_REQUIRED
}

EXTRACT_POSTING_DATA_TOOL: dict[str, Any] = {
    "name": "extract_posting_data",
    "description": (
        "공고 본문·첨부에서 EligibilityRules + 택소노미 태그 + 매칭 메타를 단일 JSON 으로 "
        "추출. 모든 신뢰도 필드는 §5 5단계 self-rating 가이드를 따른다."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "eligibility": {
                "type": "object",
                "additionalProperties": False,
                "properties": _ELIGIBILITY_PROPERTIES,
                "required": _ELIGIBILITY_REQUIRED,
                "description": (
                    "Hard Filter 입력 18 필드 nested object. 필드명 / type / nullable / "
                    "6종 인증 enum 등은 PROMPTS.md §1.1 SoT."
                ),
            },
            "field_of_work_tag_ids": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
                "description": (
                    "택소노미 노드 path (예: 'tech.ai_ml.nlp'). 시스템 프롬프트의 "
                    "{TAXONOMY_TREE} 에 박힌 path 만 허용."
                ),
            },
            "tag_confidence_per_id": {
                "type": "object",
                "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
                "description": (
                    "노드 path → 신뢰도 0-1. §5 5단계 가이드: 1.0=명시 / "
                    "0.7-0.9=확실 / 0.5-0.7=추론 / 0.3-0.5=모호 / <0.3=모름. "
                    "0.7 미만 = low-confidence (§7 분기 입력)."
                ),
            },
            "funding_uses": {
                "type": "array",
                "items": {"type": "string", "enum": _FUNDING_USES_ENUM},
                "description": (
                    "지원 자금 용도. 위 7 enum 만 허용. 본문에 명시된 항목만 emit — "
                    "도메인 prior 추정 X (예: '운영비' 명시 부재 시 '기타' 추가 금지). "
                    "명시되지 않으면 빈 배열."
                ),
            },
            "support_amount_min": {
                "type": ["integer", "null"],
                "description": "지원 금액 하한 (원 단위). 명시 없으면 null.",
            },
            "support_amount_max": {
                "type": ["integer", "null"],
                "description": "지원 금액 상한 (원 단위). 명시 없으면 null.",
            },
            "deadline_precise": {
                "type": ["string", "null"],
                "format": "date-time",
                "description": (
                    "마감 일시 (ISO 8601, 시간 미명시 시 23:59:59 KST). 명시 없으면 null."
                ),
            },
            "required_documents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "제출 서류 목록 (예: '사업자등록증', '재무제표 3개년').",
            },
            "field_confidence_scores": {
                "type": "object",
                "properties": _FIELD_CONFIDENCE_PROPERTIES,
                "required": _ELIGIBILITY_REQUIRED,
                "additionalProperties": False,
                "description": (
                    "eligibility 18 필드와 1:1 strict — 키 §1.1 EligibilityRules 필드명 "
                    "고정. §5 5단계 가이드 동일. Stage 3 분기 (PROMPTS.md §7) 의 "
                    "low-conf eligibility 카운트 결정성 보장."
                ),
            },
            "summary": {
                "type": "string",
                "maxLength": 200,
                "description": "공고 요약 200자 이내. 한국어.",
            },
            "target_description": {
                "type": "string",
                "description": (
                    "'지원대상' 섹션 정제본. 공고 본문 그대로 인용 X — 핵심 조건만 한국어 평서문."
                ),
            },
            "support_description": {
                "type": "string",
                "description": (
                    "'지원내용' 섹션 정제본. 금액·자금 용도·기간 핵심만 한국어 평서문."
                ),
            },
        },
        "required": [
            "eligibility",
            "field_of_work_tag_ids",
            "tag_confidence_per_id",
            "funding_uses",
            "support_amount_min",
            "support_amount_max",
            "deadline_precise",
            "required_documents",
            "field_confidence_scores",
            "summary",
            "target_description",
            "support_description",
        ],
    },
}
"""`extract_posting_data` tool schema (`PROMPTS.md §1` + `§1.1` mirror).

12 top-level + 18 nested eligibility 필드 모두 `required` — "absent = explicit
null 강제" 단일 정책 (`PROMPTS.md §1` line 184). LLM 정보 없을 때 omit 이 아닌
`null` literal / 빈 배열 / `false` 로 명시 → eval / M9 audit log 분석 일관성.

Stage 1 caller (commit 4) 가 `cache_control: ephemeral` 박아 호출:
    tools=[{**EXTRACT_POSTING_DATA_TOOL, "cache_control": {"type": "ephemeral"}}]
"""


@lru_cache(maxsize=1)
def get_anthropic_client() -> AsyncAnthropic:
    """`AsyncAnthropic` 싱글톤 — 내부 connection pool 재사용 + Phase 1 단일 슬롯 lazy.

    SDK default `max_retries=2` (HTTP 5xx / 429 자동 retry) + factory level
    `timeout=60.0` (CodeRabbit PR #7 F1, defense-in-depth — call site 누락 risk
    차단). 추가 외층 `asyncio.timeout(60.0)` wrapper 는 Stage 1 call site
    (`prompts.py`/`stage1.py`) 책임 (CLAUDE.md absolute rule C 만족).

    `anthropic_api_key` 미설정 시 `RuntimeError` raise — Stage 1 LLM 호출은 M4
    main 파이프라인의 critical path 라 fail-fast.
    """
    settings = get_settings()
    if settings.anthropic_api_key is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 미설정 — `.env` 또는 환경 변수 설정 필요. "
            "M4 Stage 1 LLM 호출의 critical path."
        )
    return AsyncAnthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=60.0,
        max_retries=2,
    )


async def aclose_if_initialized(logger: logging.Logger) -> None:
    """Lifespan shutdown — singleton 미초기화 시 skip + broad Exception swallow + log (double-close / SDK contract 변경 대비)."""
    if get_anthropic_client.cache_info().currsize > 0:
        try:
            await get_anthropic_client().close()
        except Exception as exc:
            logger.warning("anthropic 클라이언트 종료 실패: %s", exc, exc_info=True)


__all__ = ["EXTRACT_POSTING_DATA_TOOL", "aclose_if_initialized", "get_anthropic_client"]
