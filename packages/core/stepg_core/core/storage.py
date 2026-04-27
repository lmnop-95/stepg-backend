"""Storage backend abstraction — Phase 1 LocalFs, Phase 1.5 R2/S3 swap target.

`StorageBackend` is the structural interface (Q36: `Protocol` + async). M2
commit 4 lands `LocalFsBackend`; the registry/Settings owns the singleton
selection later.

Phase 1 layout (Q8): `{storage_root}/attachments/{hash[:2]}/{hash}` — content-
hash sharded, no extension on disk (the metadata lives in `Attachment` rows).
Same hash put twice is idempotent (LocalFsBackend.put_path returns the
existing path and discards the source temp file).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

_HASH_LENGTH = 64
_HEX_CHARS = frozenset("0123456789abcdef")


@runtime_checkable
class StorageBackend(Protocol):
    """Async storage interface — content-hash addressed.

    `put_path` / `exists` / `path` operate on SHA-256 hex digests (`String(64)`
    per M1 schema). Backends never see file *names*; the caller persists them
    in the `Attachment` row.

    Streaming contract (Q57): caller writes bytes into a temp file (chunked
    SHA-256 along the way) and hands the *path* to the backend. LocalFs does
    `Path.replace()` for atomic move; R2/S3 (Phase 1.5) does multipart upload.
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


def _validate_hash(content_hash: str) -> None:
    """Path-traversal guard + M1 `String(64)` consistency check (Q77).

    Backends address by hash; rejecting non-canonical input here keeps
    `{root}/{hash[:2]}/{hash}` from resolving outside `root` regardless of
    backend. Caller (commit 5) computes hashes from streaming SHA-256 so a
    malformed hash here is a programmer bug, not external input.
    """
    if len(content_hash) != _HASH_LENGTH or not all(c in _HEX_CHARS for c in content_hash):
        raise ValueError(
            f"content_hash는 SHA-256 hex 64자(소문자 a-f, 0-9)여야 합니다 "
            f"(입력 길이 {len(content_hash)})"
        )


class LocalFsBackend(StorageBackend):
    """Local filesystem `StorageBackend` (Phase 1).

    Explicit `StorageBackend` inheritance (Q80): Protocol method drift is
    surfaced at *class definition* time by pyright instead of deferring to
    the first caller annotation. Phase 1.5 R2/S3 backend follows the same
    pattern.

    `root` is the *attachments* base — caller passes
    `Settings.storage_root / "attachments"` (Q71) so `LocalFsBackend` is
    agnostic to the wider storage tree (M3 parsed-output dir, Phase 1.5
    auxiliary stores, etc.).

    Sync syscalls (Q76): `Path.replace` / `Path.exists` are microsecond-scale
    — wrapping in `asyncio.to_thread` would add overhead without measurable
    event-loop relief. R2/S3 (Phase 1.5) will introduce real I/O latency and
    swap to native async clients then.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def _dst(self, content_hash: str) -> Path:
        _validate_hash(content_hash)
        return self._root / content_hash[:2] / content_hash

    async def put_path(self, content_hash: str, src: Path) -> Path:
        """Atomic move `src` → `{root}/{hash[:2]}/{hash}`.

        Idempotent (Q73): if the destination already exists, the source temp
        file is unlinked and the existing path is returned — the caller's
        download wasted bandwidth but the on-disk state is consistent.
        `Path.replace` (Q72) wraps POSIX `rename(2)`, atomic on the same
        filesystem; the temp file lives under the same `storage_root` so
        cross-FS rename is not a concern in Phase 1.

        Caller must guarantee `src` exists. `missing_ok=True` on the unlink
        covers concurrent unlink (Phase 1.5 worker-pool race), not absence —
        an absent `src` from a buggy caller silently no-ops the unlink and
        returns the prior `dst`, which would mask the bug.

        Sync `pathlib` calls inside an async function (Q76): tolerated for
        microsecond-scale syscalls; revisit when R2/S3 backend lands.
        """
        dst = self._dst(content_hash)
        if dst.exists():  # noqa: ASYNC240 — Q76 sync syscall (microsecond)
            src.unlink(missing_ok=True)  # noqa: ASYNC240
            return dst
        dst.parent.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
        src.replace(dst)  # noqa: ASYNC240
        return dst

    async def exists(self, content_hash: str) -> bool:
        return self._dst(content_hash).exists()  # noqa: ASYNC240 — Q76

    async def path(self, content_hash: str) -> Path:
        """Return the on-disk path *without* existence check (Q75).

        Caller is expected to `await exists()` first. Phase 1.5 R2/S3 `path()`
        will fetch the object into a local temp file and return that path,
        so a missing-file check here would diverge from remote-backend
        semantics. Local missing file ⇒ caller-side bug.
        """
        return self._dst(content_hash)


__all__ = ["LocalFsBackend", "StorageBackend"]
