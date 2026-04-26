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

    `put` / `exists` / `path` operate on SHA-256 hex digests (`String(64)` per
    M1 schema). Backends never see file *names*; the caller persists them in
    the `Attachment` row. R2/S3 swap (Phase 1.5) keeps this surface and only
    rewrites the implementation body.
    """

    async def put(self, content_hash: str, data: bytes) -> Path: ...

    async def exists(self, content_hash: str) -> bool: ...

    async def path(self, content_hash: str) -> Path: ...


__all__ = ["StorageBackend"]
