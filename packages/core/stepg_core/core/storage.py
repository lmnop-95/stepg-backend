"""Storage backend abstraction — Phase 1 LocalFs, Phase 1.5 R2/S3 swap target.

`StorageBackend` is the structural interface (Q36: `Protocol` + async). M2
commit 4 lands `LocalFsBackend`; the registry/Settings owns the singleton
selection later.

Phase 1 layout (Q8): `{storage_root}/attachments/{hash[:2]}/{hash}` — content-
hash sharded, no extension on disk (the metadata lives in `Attachment` rows).
Same hash put twice is idempotent (commit 4 implements the no-op).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class StorageBackend(Protocol):
    """Async storage interface — content-hash addressed.

    `put_path` / `exists` / `path` operate on SHA-256 hex digests (`String(64)`
    per M1 schema). Backends never see file *names*; the caller persists them
    in the `Attachment` row.

    Streaming contract (Q57): caller writes bytes into a temp file (chunked
    SHA-256 along the way) and hands the *path* to the backend. LocalFs does
    `os.replace()` for atomic move; R2/S3 (Phase 1.5) does multipart upload.
    Whole-buffer `bytes` interface would force callers to load multi-MB files
    into memory at once — cron processing 100+ rows per day would peak in
    GB-range.

    `path()` returns a local `Path` even for remote backends — Phase 1.5 R2/S3
    `path()` will fetch + write to a local temp dir + return that path
    (caller treats it as ephemeral). M3 parsers (pdfplumber/pyhwpx) need a
    file-system path either way (Q67).
    """

    async def put_path(self, content_hash: str, src: Path) -> Path: ...

    async def exists(self, content_hash: str) -> bool: ...

    async def path(self, content_hash: str) -> Path: ...


__all__ = ["StorageBackend"]
