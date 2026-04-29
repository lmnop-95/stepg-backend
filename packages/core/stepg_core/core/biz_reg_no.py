"""사업자등록번호 정규화 — pitfalls D 정책 단일 SoT.

`Company.biz_reg_no` 는 dash / 공백 등 구분자를 제거한 10자리 raw digit 문자열로
저장한다 (`docs/legacy/pitfalls.md` §M5 D). 이 정책을 두 곳 (M5 onboarding
schema validator + CLOVA OCR 매핑) 에서 호출하므로, 알고리즘 (regex strip + 길이
검증) 을 본 모듈에 단일 SoT 로 둔다.

호출 측 분기:
- schema validator: None → ko-KR `ValueError` 로 변환 → Pydantic 422
- CLOVA 매핑: None → 그대로 사용 (OCR 결과가 10자리 미만이면 DTO 필드 None)

`fetch_with_retry` (`core/http.py`) 와 동일한 cross-feature `core/` 레이어 패턴.
"""

from __future__ import annotations

import re
from typing import Final

_NON_DIGITS_RE: Final[re.Pattern[str]] = re.compile(r"\D+")
_BIZ_REG_NO_LEN: Final[int] = 10


def normalize_to_digits(raw: str) -> str | None:
    """raw 입력에서 숫자만 추출, 정확히 10자리면 반환, 아니면 None."""
    digits = _NON_DIGITS_RE.sub("", raw)
    if len(digits) != _BIZ_REG_NO_LEN:
        return None
    return digits


__all__ = ["normalize_to_digits"]
