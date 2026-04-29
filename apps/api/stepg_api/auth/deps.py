"""Auth dependencies — dev placeholder (commit 7~8) → NextAuth JWT (commit 9).

`get_current_user_id` is the `Depends(...)` injection point for routes that
need an authenticated user (`POST /onboarding/complete` is the first user).

Commit 9 (`auth/nextauth_jwt.py`) will replace this module's body with HS256
JWT verification (Q3 plan-stage — `NEXTAUTH_SECRET` shared secret) so the
route signature stays stable across commits.

Until then, dev mode reads the `DEV_USER_ID` env (default `1`) so curl /
local FE flows can exercise the route against a pre-seeded user row.

Q2 pass5 — module-top guard blocks `app_env == "production"` import. This
is defense-in-depth for the gap between commit 7 (dev stub lands) and commit
9 (NextAuth JWT swap-in). Import-time loud-fail is preferable to per-request
guard because the API process never reaches `uvicorn.run` if the stub is
shipped to production by mistake. `RuntimeError` (not `assert`) so `python -O`
cannot strip the check.
"""

from __future__ import annotations

import os
from typing import Final

from stepg_core.core.config import get_settings

if get_settings().app_env == "production":
    raise RuntimeError(
        "stepg_api.auth.deps is a dev stub — must be replaced by NextAuth JWT "
        "verification (commit 9) before production deployment"
    )

_DEV_USER_ID_ENV: Final[str] = "DEV_USER_ID"
_DEV_USER_ID_DEFAULT: Final[int] = 1


def get_current_user_id() -> int:
    """Return the user_id for the current request.

    Dev stub — reads `DEV_USER_ID` env (default `1`). The route will FK-fail
    unless a `users` row with that id exists; seed manually for dev.
    """
    raw = os.getenv(_DEV_USER_ID_ENV)
    if raw is None:
        return _DEV_USER_ID_DEFAULT
    try:
        return int(raw)
    except ValueError:
        return _DEV_USER_ID_DEFAULT


__all__ = ["get_current_user_id"]
