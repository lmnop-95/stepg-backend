"""Domain-level error types shared across features.

`HttpFetchError` is M2's contribution; M4/M5 will append OCR/LLM-class errors
here so feature modules import from a single anchor.

Legacy lessons baked in (`docs/legacy/pitfalls.md` §M2 C3/C4):
- URL stripped of query string before storage in `url` (handled by callers via
  `core.http._safe_url`); secrets never reach this layer.
- HTTP error response bodies are *not* preserved — only `status` + caller-side
  metadata. Bodies may contain PII (담당자 이메일/전화) and must not propagate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)
class HttpFetchError(Exception):
    url: str
    status: int | None
    attempt: int
    cause: BaseException | None

    def __str__(self) -> str:
        cause = f" caused_by={type(self.cause).__name__}" if self.cause is not None else ""
        return f"HttpFetchError(url={self.url} status={self.status} attempt={self.attempt}){cause}"


class BizinfoSchemaError(Exception):
    """bizinfo response shape unexpectedly changed (envelope/key/list-element).

    Raised by `sources/bizinfo.py::_extract_items`. Distinct from `HttpFetchError`
    (network/status) and `RuntimeError` (Python-level bug) so the cron entry in
    `service.py::ingest_postings` can demote source-level shape failures to a
    warning + skip without swallowing genuine code bugs (Pass 11 Rule 1 — narrow
    catch).
    """


class MissingApiKeyError(Exception):
    """Source adapter invoked without its API key in `Settings`.

    Raised by `sources/bizinfo.py::fetch` when `BIZINFO_API_KEY` env is unset.
    Same demotion rationale as `BizinfoSchemaError` — caller treats as "skip
    source, continue cron" rather than crashing the whole ingest cycle.
    """


class UnsupportedAttachmentFormatError(Exception):
    """Attachment filename suffix not in M3 dispatch matrix.

    Raised by `features/parsing/service.parse_attachment` when the suffix
    is not one of `.pdf` / `.hwpx` / `.docx`. Callers (M3 commit 6
    `parse_attachments`) demote to `parse_status='skipped_unsupported'` +
    WARNING log + posting 통과 (Q6/Q7 정책). ARCHITECTURE §1.1 "HWP 레거시
    미지원" 명시 정책과 동일 처리 (`.hwp` 확장자도 본 예외).
    """

    def __init__(self, *, suffix: str, filename: str) -> None:
        super().__init__(f"unsupported attachment format: suffix={suffix!r} filename={filename!r}")
        self.suffix = suffix
        self.filename = filename


class OcrCallError(Exception):
    """Domain-level OCR failure surfaced to the route layer (Q23 / Q5 pass3).

    `code` is a stable snake_case identifier (Q8); `message` carries upstream
    wording for log / inspection only — the route layer maps `code` to a
    Korean user-facing detail via its own lookup table (Q2 pass3 contract:
    `OcrCallError.message` is *internal*, never surfaced to FE). `http_status`
    is None for our own pre-call validation (e.g. misconfiguration, timeout)
    and populated when the failure originates from a CLOVA HTTP response.

    Defined here (M2/M3 pattern) so that `features/onboarding/sources/`,
    `features/onboarding/upload_validator.py`, and `apps/api/.../routes/`
    share a single anchor without sub-module cross-imports.
    """

    def __init__(self, *, code: str, message: str, http_status: int | None = None) -> None:
        super().__init__(f"OcrCallError(code={code} status={http_status})")
        self.code = code
        self.message = message
        self.http_status = http_status


class OnboardingError(Exception):
    """Domain-level onboarding failure raised by the service layer (Q52).

    `code` is a stable snake_case identifier (Q8 convention) — the route layer
    maps it to a Korean detail via `_ONBOARDING_DOMAIN_ERROR_KO`. Distinct from
    `IntegrityError` (Postgres UNIQUE violation): `OnboardingError` covers
    pre-write validation that can fail without touching the DB write path
    (currently `fields_of_work_invalid` — input UUID 가 미존재 / deprecated).
    """

    def __init__(self, *, code: str) -> None:
        super().__init__(f"OnboardingError(code={code})")
        self.code = code


__all__ = [
    "BizinfoSchemaError",
    "HttpFetchError",
    "MissingApiKeyError",
    "OcrCallError",
    "OnboardingError",
    "UnsupportedAttachmentFormatError",
]
