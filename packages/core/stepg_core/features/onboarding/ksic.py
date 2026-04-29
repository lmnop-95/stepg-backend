"""KSIC code lookup — `bisType` 한국어 → KSIC 코드 변환.

Phase 1 매칭 정책 (Q42): 정확한 name 일치 (case-insensitive + whitespace
normalize). 다중 매치 시 가장 짧은 코드 (즉 가장 상위 분류) 우선 — recon
`bisType="정보통신업"` 같은 대분류 명을 받으면 대분류 J (1글자) 가 매칭됨.
fuzzy / alias / hierarchy 검색은 Phase 1.5 (M6 매칭 누락률 측정 후 도입).

호출자 (commit 7 `POST /onboarding/complete`): `OcrBizRegResponse.business_types`
(dedupe 된 `tuple[str, ...]`) 전체를 `lookup_first_ksic_code` 에 넘겨 첫 매치
코드 반환 — Q43 "all match, 첫 non-None" 안전망.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from stepg_core.features.onboarding.models import Ksic

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.ext.asyncio import AsyncSession


def _normalize(name: str) -> str:
    # Q5 pass4: bare `str.split()` 가 이미 leading/trailing whitespace 무시 +
    # 모든 internal whitespace runs 를 collapse → 별도 `.strip()` 불필요.
    return " ".join(name.split()).lower()


async def lookup_ksic_code_by_name(session: AsyncSession, name: str) -> str | None:
    """단일 분류명을 KSIC 코드로 변환 (Q42 정확 일치).

    `name` 을 lowercase + collapse-whitespace 정규화한 뒤 `Ksic.name` (이미
    insert 시점에 canonical whitespace 로 저장됨, Q1 pass4) 의 lowercase 와
    비교. 다중 매치 시 가장 짧은 코드 (상위 분류) 우선.
    """
    normalized = _normalize(name)
    if not normalized:
        return None
    stmt = (
        select(Ksic.code)
        .where(func.lower(Ksic.name) == normalized)
        .order_by(func.length(Ksic.code))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def lookup_first_ksic_code(session: AsyncSession, names: Iterable[str]) -> str | None:
    """Q43: `names` 를 순서대로 시도, 첫 non-None 반환.

    `OcrBizRegResponse.business_types` 가 dedupe 된 다중 업종 (예: 동일 업종
    4중복 → 1) 또는 multi-business (예: 정보통신업 + 도매업) 일 때 안전망.
    """
    for name in names:
        code = await lookup_ksic_code_by_name(session, name)
        if code is not None:
            return code
    return None


__all__ = ["lookup_first_ksic_code", "lookup_ksic_code_by_name"]
