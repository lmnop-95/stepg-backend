"""NextAuth JWT verification — HS256 signed token → `users.id` integer.

`verify_session_jwt(token)` is the only public entry point; `auth/deps.py::
get_current_user_id` calls it after extracting the Bearer token from the
request `Authorization` header.

Decisions (Q57~Q60, Q62 — plan.md commit 9 Batch B):
- HS256 shared secret with NextAuth.js — FE 측 `session: { strategy: "jwt" }`
  signed-only 설정 강제 (Q60). v5 default JWE는 Phase 1.5에서 별도 결정.
- `sub` claim에 `users.id` integer string이 박혀 있다고 신뢰 (Q59) — NextAuth
  + Prisma/Drizzle DB adapter 표준. 미일치 케이스는 Phase 1.5에 jwt callback
  으로 FE 협조.
- `exp` claim 강제 (`require=["exp"]`) — 만료 없는 영구 토큰 차단.
- `InvalidTokenError` 계열 (`ExpiredSignatureError` 포함) → `JwtVerifyError` 로
  통합 (Q62 정보 누설 차단). route 가 단일 401 ko-KR 로 매핑.

Phase 1: `aud` / `iss` claim 검증 deferred — single FE / single-secret 가정
(Q1pass7). Phase 1.5 환경 분리 (`docs/ARCHITECTURE.md` §10) 시 `Settings.
nextauth_url` 추가 + `verify_aud=True / verify_iss=True / audience=... /
issuer=...` 조합으로 token reuse / cross-app replay 차단.
"""

from __future__ import annotations

from typing import Final

import jwt
from stepg_core.core.config import get_settings

_ALGORITHM: Final[str] = "HS256"


class JwtVerifyError(Exception):
    """NextAuth JWT 검증 실패 — invalid / expired / missing-claim 등 통합."""


def verify_session_jwt(token: str) -> int:
    """HS256 검증 후 `sub` claim → `users.id` int 반환.

    실패 시 `JwtVerifyError` raise — caller (auth/deps.py) 가 401 변환.
    `nextauth_secret` 미설정 (dev `app_env`) 인데 본 함수가 호출되면
    `JwtVerifyError("nextauth_secret unset")` — `auth/deps.py::
    get_current_user_id` 가 dev fallback (DEV_USER_ID) 으로 진입했어야 하는
    경로이므로 본 함수 도달은 misconfiguration 신호.
    """
    secret = get_settings().nextauth_secret
    if secret is None:
        raise JwtVerifyError("nextauth_secret unset")

    try:
        payload = jwt.decode(
            token,
            secret.get_secret_value(),
            algorithms=[_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError as e:
        raise JwtVerifyError(str(e)) from e

    sub = payload["sub"]
    if not isinstance(sub, str):
        raise JwtVerifyError(f"sub claim is not a string (got {type(sub).__name__})")
    try:
        return int(sub)
    except ValueError as e:
        raise JwtVerifyError(f"sub claim is not an integer: {sub!r}") from e


__all__ = ["JwtVerifyError", "verify_session_jwt"]
