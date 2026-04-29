"""Onboarding orchestration — `complete_onboarding` (commit 7) +
`Project` 적재 + tx atomicity (commit 8).

Commit 7: Company 단일 적재 + KSIC lookup. commit 8 이 같은 함수 안에서
default Project 생성 + `project_fields_of_work` M2M 삽입을 추가하고 전체를
`async with session.begin():` 으로 atomic 보장 (M5 commit 8 의도).

Q48 plan: KSIC lookup 은 service 단 (route 가 input.business_types 그대로
넘김 → service 가 DB lookup → Company 매핑).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from stepg_core.features.companies.models import Company
from stepg_core.features.onboarding.ksic import lookup_first_ksic_code

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from stepg_core.features.onboarding.schemas import OnboardingCompleteRequest


async def complete_onboarding(
    session: AsyncSession,
    request: OnboardingCompleteRequest,
    user_id: int,
) -> Company:
    """OCR 검수 완료 input 으로 `Company` 1건 적재 후 반환.

    KSIC code 는 `request.business_types` 다중 element 를 순차 lookup 한 첫
    non-None (Q43). 매치 실패 시 `Company.industry_ksic_code = NULL` —
    매칭 엔진(M6) 이 KSIC 없는 Company 를 어떻게 다룰지 별도 정책.

    commit 8 에서 default Project 생성 + `project_fields_of_work` M2M 삽입을
    이 함수 안에 추가하고 `async with session.begin():` 로 전체 atomic 보장
    예정. commit 7 단계에서는 caller (route) 가 commit 호출.
    """
    industry_ksic_code = await lookup_first_ksic_code(session, request.business_types)

    company = Company(
        user_id=user_id,
        biz_reg_no=request.biz_reg_no,
        corporate_type=request.corporate_type,
        established_on=request.established_on,
        employee_count=request.employee_count,
        revenue_last_year=request.revenue_last_year,
        sido=request.sido,
        certifications=list(request.certifications),
        industry_ksic_code=industry_ksic_code,
    )
    session.add(company)
    await session.flush()
    return company


__all__ = ["complete_onboarding"]
