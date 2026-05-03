"""Onboarding orchestration — `complete_onboarding` (commit 7~8).

Commit 7: Company 단일 적재 + KSIC lookup. commit 8 가 같은 함수 안에 default
Project 생성 + `project_fields_of_work` M2M 삽입을 추가하고 전체를
`async with session.begin():` 으로 atomic 보장 (M5 commit 8 의도).

Q48: KSIC lookup 위치 = service 단 (route 가 input.business_types 그대로 넘김
→ service 가 DB lookup → Company 매핑).

Q51: `Project.name` default = `"기본 프로젝트"` (사용자가 추후 별도 endpoint 로
변경, M5 outside scope).

Q52: `fields_of_work_ids` 사전 SELECT validate — 3개 모두 미존재 또는
`deprecated_at` 가 NULL 이 아니면 `OnboardingError("fields_of_work_invalid")`
raise (atomic tx 진입 전 차단). FK violation 으로 IntegrityError 흘려보내면
constraint name 분기 + tx rollback 비용↑ + ko-KR 메시지 매핑 부담.

Q53: M2M 삽입 = SQLAlchemy core `insert(project_fields_of_work).values(...)`
(M1 model 에 relationship 미선언 → 직접 INSERT 가 자연).

Q54: `async with session.begin():` 로 service 단 atomic. Company UNIQUE 위반
(`uq_companies_biz_reg_no` / `uq_companies_user_id`) 시 IntegrityError 가
block exit 시점에 raise — 전체 rollback 자동. route 가 catch + 409.

Q55: 반환값 = `tuple[Company, Project]` — Pythonic + type hint 명확.

Q56: M2M insert 후 추가 flush 미호출 — block exit 시 자동 commit + flush 가
처리. Company / Project 만 명시적 flush (PK 필요).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sqlalchemy import insert, select
from stepg_core.core.errors import OnboardingError
from stepg_core.features.companies.models import Company
from stepg_core.features.fields_of_work.models import FieldOfWork
from stepg_core.features.onboarding.ksic import lookup_first_ksic_code
from stepg_core.features.projects.models import Project, project_fields_of_work

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession
    from stepg_core.features.onboarding.schemas import OnboardingCompleteRequest

_DEFAULT_PROJECT_NAME: Final[str] = "기본 프로젝트"


async def complete_onboarding(
    session: AsyncSession,
    request: OnboardingCompleteRequest,
    user_id: int,
) -> tuple[Company, Project]:
    """OCR 검수 완료 input 으로 `Company` + default `Project` + M2M 적재.

    KSIC code 는 `request.business_types` 다중 element 를 순차 lookup 한 첫
    non-None (Q43). 매치 실패 시 `Company.industry_ksic_code = NULL` —
    매칭 엔진(M6) 이 KSIC 없는 Company 를 어떻게 다룰지 별도 정책.

    `async with session.begin():` 가 SELECT (validate / KSIC lookup) + INSERT
    (Company / Project / M2M) 전체를 단일 transaction 으로 감싼다 — block 안
    에서 `OnboardingError` 가 raise 되거나 IntegrityError 가 발화하면 block
    exit 가 자동 rollback. SELECT 를 block *바깥* 에 두면 implicit tx 가 미리
    열려 `session.begin()` 가 `InvalidRequestError("transaction is already
    begun")` 으로 실패한다.
    """
    async with session.begin():
        await _validate_fields_of_work(session, request.fields_of_work_ids)
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

        project = Project(
            company_id=company.id,
            name=_DEFAULT_PROJECT_NAME,
            is_default=True,
        )
        session.add(project)
        await session.flush()

        await session.execute(
            insert(project_fields_of_work).values(
                [
                    {"project_id": project.id, "field_of_work_id": fid}
                    for fid in request.fields_of_work_ids
                ]
            )
        )

    return company, project


async def _validate_fields_of_work(
    session: AsyncSession,
    ids: tuple[UUID, UUID, UUID],
) -> None:
    found = set(
        await session.scalars(
            select(FieldOfWork.id).where(
                FieldOfWork.id.in_(ids),
                FieldOfWork.deprecated_at.is_(None),
            )
        )
    )
    if len(found) != len(ids):
        raise OnboardingError(code="fields_of_work_invalid")


__all__ = ["complete_onboarding"]
