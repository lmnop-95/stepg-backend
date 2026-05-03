"""Auth dependencies — Authorization Bearer 추출 + NextAuth JWT 검증.

`get_current_user_id` 는 `Depends(...)` injection point — `/onboarding/*`
router-level dependency (`main.py::app.include_router(deps=...)`) + 필요 시
path-level 에서 user_id 값 사용.

Decisions (Q60~Q64 — plan.md commit 9 Batch B):
- Q60: 토큰 = `Authorization: <scheme> <token>` header. scheme 은 RFC 6750
  §2.1 정합 case-insensitive ("Bearer" / "bearer" / "BEARER" 모두 수용).
  cookie / JWE 는 Phase 1.5.
- Q61: `/onboarding/*` 전체 보호 — `/ocr` 도 (CLOVA 비용 abuse 차단).
- Q62: invalid / expired / missing 모두 `401 unauthorized` 동일 응답
  (timing attack / 정보 누설 차단).
- Q63: verify 책임은 `auth/nextauth_jwt.py`. 본 모듈은 entry-point + dev
  fallback. commit 7 의 production guard (RuntimeError) 는 commit 9 swap 으로
  무용 — 제거.
- Q64: `app_env == "development"` 분기 — `DEV_USER_ID` env 가 비어있지 않을
  때 fallback (curl / 단위 테스트 호환). 빈 문자열은 unset 과 동일 취급
  (Settings `env_ignore_empty=True` semantic 일관, Q4pass7). staging/production
  은 항상 JWT 강제.
"""

from __future__ import annotations

import os
from typing import Final

from fastapi import HTTPException, Request, status
from stepg_core.core.config import get_settings

from stepg_api.auth.nextauth_jwt import JwtVerifyError, verify_session_jwt

_DEV_USER_ID_ENV: Final[str] = "DEV_USER_ID"
_BEARER_SCHEME: Final[str] = "bearer"

_UNAUTHORIZED_DETAIL: Final[dict[str, str]] = {
    "code": "unauthorized",
    "message": "세션이 만료되었거나 인증되지 않았습니다.",
}


def _unauthorized() -> HTTPException:
    # WWW-Authenticate 표준 (RFC 6750) — FE 가 challenge scheme 인식 가능.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_UNAUTHORIZED_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_id(request: Request) -> int:
    """Return the `users.id` for the current request."""
    if get_settings().app_env == "development":
        dev_user_id = os.getenv(_DEV_USER_ID_ENV)
        if dev_user_id:
            try:
                return int(dev_user_id)
            except ValueError as e:
                raise _unauthorized() from e

    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != _BEARER_SCHEME or not token:
        raise _unauthorized()

    try:
        return verify_session_jwt(token)
    except JwtVerifyError as e:
        raise _unauthorized() from e


__all__ = ["get_current_user_id"]
