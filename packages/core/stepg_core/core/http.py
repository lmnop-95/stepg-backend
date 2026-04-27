"""Shared HTTP fetch util — single retry source of truth.

CLAUDE.md absolute rule C: every external HTTP call must have timeout + retry.
M2 lands this util; M4 (Anthropic), M5 (CLOVA OCR), Resend reuse the same anchor.

Design (`docs/.local/feat-ingestion-M2-bizinfo/plan.md` Q1/Q2/Q20/Q33/Q38, legacy
`docs/legacy/assets.md` §1):
- `httpx.AsyncClient(timeout=15.0, follow_redirects=True)` per call (no pooling
  yet; Phase 1.5 may switch to module singleton).
- `httpx.HTTPTransport(retries=...)` is left at the default (off). tenacity is
  the single retry source — double-retry would compound backoff.
- `tenacity` decorator wraps the call; per-attempt `asyncio.timeout(...)` is the
  caller's responsibility (`async with asyncio.timeout(N): ...`) — function-level
  `timeout=` parameters trip ruff `ASYNC109`.
- 429 is retried (공공데이터포털 `TRAFFIC_EXCEEDED` quota cycling); permanent
  4xx fails fast — quota burn ≠ retry intent.
- Error messages carry only `content_type` + `body_len` (legacy C4); the upstream
  body may contain PII.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

from stepg_core.core.errors import HttpFetchError

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 15.0
_MAX_ATTEMPTS = 3
_STOP_AFTER_DELAY_SECONDS = 60.0
_RETRIABLE_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def _safe_url(url: str) -> str:
    """Strip query string — secrets (e.g. `crtfcKey`) live there.

    legacy `docs/legacy/pitfalls.md` §M2 C3: structlog `mask_pii` matches by
    field name, not by URL substring, so query strings leak verbatim into logs
    unless stripped here.
    """
    return url.split("?", 1)[0]


def _is_retriable_status(status: int) -> bool:
    return status in _RETRIABLE_STATUS


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return _is_retriable_status(exc.response.status_code)
    return False


async def fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    json: Any | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    """Issue an HTTP request with shared retry policy.

    Returns the `httpx.Response` on success (after `raise_for_status()`).
    Raises `HttpFetchError` after the final attempt — caller never sees
    `httpx.HTTPStatusError` directly so log/Sentry messages never include the
    upstream body (legacy C4).
    """

    safe = _safe_url(url)
    last_status: int | None = None
    last_attempt = 0
    last_cause: BaseException | None = None

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_ATTEMPTS) | stop_after_delay(_STOP_AFTER_DELAY_SECONDS),
            wait=wait_exponential_jitter(initial=1.0, max=4.0),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        ):
            with attempt:
                last_attempt = attempt.retry_state.attempt_number
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=json,
                    content=content,
                )
                if _is_retriable_status(response.status_code):
                    logger.warning(
                        "http retry status=%d url=%s attempt=%d",
                        response.status_code,
                        safe,
                        last_attempt,
                    )
                response.raise_for_status()
                return response
    except RetryError as e:  # pragma: no cover — reraise=True suppresses RetryError
        last_cause = e.last_attempt.exception() if e.last_attempt else None
    except httpx.HTTPStatusError as e:
        last_status = e.response.status_code
        last_cause = e
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        last_cause = e

    body_len = "n/a"
    content_type = "n/a"
    if isinstance(last_cause, httpx.HTTPStatusError):
        body_len = str(len(last_cause.response.content))
        content_type = last_cause.response.headers.get("content-type", "n/a")

    logger.error(
        "http fetch failed url=%s status=%s attempt=%d content_type=%s body_len=%s",
        safe,
        last_status,
        last_attempt,
        content_type,
        body_len,
    )
    raise HttpFetchError(url=safe, status=last_status, attempt=last_attempt, cause=last_cause)


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "fetch_with_retry",
]
