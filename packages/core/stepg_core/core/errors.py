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


__all__ = ["HttpFetchError"]
