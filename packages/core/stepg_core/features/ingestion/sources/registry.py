"""Source registry — `Callable` alias dodges pyright #5026 (legacy C5)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from stepg_core.features.ingestion.schemas import RawPostingPayload, SourceKind
from stepg_core.features.ingestion.sources import bizinfo

SourceFetcher = Callable[[], Awaitable[list[RawPostingPayload]]]
SOURCES: dict[SourceKind, SourceFetcher] = {"bizinfo": bizinfo.fetch}

__all__ = ["SOURCES", "SourceFetcher"]
