"""Pydantic 모델 — `EligibilityRules` (M6 Hard Filter input) + `ExtractedPostingData`
(full LLM output, `Posting.extracted_data` JSONB 적재 양식).

`docs/ARCHITECTURE.md §4.1` (18 eligibility 필드) + `§4.2` (12 top-level 필드) mirror.
M4 service boundary 검증 — `Posting.eligibility` / `extracted_data` JSONB 컬럼은
ORM 측 `dict[str, Any] | None` 약 type, strict shape 은 본 모듈 (`features/postings/models.py`
docstring line 1-12 SoT).

Stage 2 (`stage2.py`) 가 LLM 출력 → `ExtractedPostingData.model_validate()` 검증 +
per-field fallback (eligibility 만, `PROMPTS.md §6` step 5). commit 7 service 가
`extracted.eligibility.model_dump()` → `Posting.eligibility` 컬럼 + `extracted.model_dump()`
→ `Posting.extracted_data` 컬럼 dual-write (plan.md commit 7 invariant).

KSIC field validator: 숫자만 허용 (대분류 알파벳 prefix 제외, `PROMPTS.md §1.1` line 205
+ `TAXONOMY.md §4.1` SoT). 6종 인증 / 7종 funding_uses Literal enum strict.
sido 광역명은 free `str` — "전국" / 권역명 등 자유 표현 허용 (Pass 4 critic Q27=2).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ARCHITECTURE.md §4.1 + §8.2 — 6종 인증 enum (Posting eligibility + Company.certifications
# 양쪽 동일 SoT). `anthropic_client.py::_CERTIFICATION_ENUM` mirror.
CertificationLiteral = Literal[
    "벤처기업",
    "이노비즈",
    "메인비즈",
    "여성기업",
    "장애인기업",
    "소셜벤처",
]

# ARCHITECTURE.md §4.2 — funding_uses 7종 enum.
# `anthropic_client.py::_FUNDING_USES_ENUM` mirror.
FundingUseLiteral = Literal[
    "R&D",
    "시설투자",
    "채용",
    "수출",
    "교육",
    "운영자금",
    "기타",
]

_KSIC_PATTERN = re.compile(r"^[0-9]{2,5}$")


def _empty_funding_uses() -> list[FundingUseLiteral]:
    """`Field(default_factory=...)` 양식 통일용 typed factory — pyright가 `list` 의
    element type을 추론 못 해 `list[Unknown]` warning 발생, typed return으로 우회."""
    return []


class EligibilityRules(BaseModel):
    """`ARCHITECTURE.md §4.1` 18 필드 mirror — M6 Hard Filter SQL where 절 입력.

    18 필드 모두 default 박힘 (LLM omit 안전망) — tool input_schema가 LLM 측에서
    "absent = explicit null/false/[] 강제" 보장 (`PROMPTS.md §1` line 184). Pydantic
    측 default는 LLM 응답 변형 시 graceful — Stage 2 fallback과 dual layer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    corporate_types_allowed: list[str] | None = None
    corporate_types_excluded: list[str] | None = None
    employee_count_min: int | None = None
    employee_count_max: int | None = None
    revenue_last_year_min: int | None = None
    revenue_last_year_max: int | None = None
    years_in_business_min: int | None = None
    years_in_business_max: int | None = None
    location_required_sido: list[str] | None = None
    location_preferred_sido: list[str] | None = None
    location_excluded_sido: list[str] | None = None
    industry_ksic_allowed: list[str] | None = None
    industry_ksic_excluded: list[str] | None = None
    certifications_required: list[CertificationLiteral] | None = None
    certifications_preferred: list[CertificationLiteral] | None = None
    certifications_excluded: list[CertificationLiteral] | None = None
    prior_recipients_excluded: bool = False
    free_text_conditions: list[str] = Field(default_factory=list)

    @field_validator("industry_ksic_allowed", "industry_ksic_excluded", mode="after")
    @classmethod
    def _validate_ksic_codes(cls, v: list[str] | None) -> list[str] | None:
        """KSIC 코드는 숫자만 — 대분류 알파벳 prefix 제외 (`PROMPTS.md §1.1` line 205).

        통계청 KSIC 10차 자릿수: 2-5자리 숫자 (중분류~세세분류). 대분류 알파벳 prefix
        는 외부 DB 양식 — 본 시스템 적재 양식 정합 X.
        """
        if v is None:
            return v
        for code in v:
            if not _KSIC_PATTERN.match(code):
                raise ValueError(f"KSIC 코드는 숫자만 허용 (대분류 알파벳 prefix 제외): {code!r}")
        return v


class ExtractedPostingData(BaseModel):
    """`ARCHITECTURE.md §4.2` 12 top-level 필드 mirror — LLM Stage 1 출력 전체.

    `Posting.extracted_data` JSONB 풀 dump (commit 7) + `eligibility` 별 컬럼
    (`Posting.eligibility`) dual-write — M6 Hard Filter SQL where 절 빠른 access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    eligibility: EligibilityRules
    field_of_work_tag_ids: list[str] = Field(default_factory=list)
    tag_confidence_per_id: dict[str, float] = Field(default_factory=dict)
    funding_uses: list[FundingUseLiteral] = Field(default_factory=_empty_funding_uses)
    support_amount_min: int | None = None
    support_amount_max: int | None = None
    deadline_precise: datetime | None = None
    required_documents: list[str] = Field(default_factory=list)
    field_confidence_scores: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
    target_description: str = ""
    support_description: str = ""


__all__ = [
    "CertificationLiteral",
    "EligibilityRules",
    "ExtractedPostingData",
    "FundingUseLiteral",
]
