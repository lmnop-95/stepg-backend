"""Ingestion pipeline orchestrator — placeholder for commit 1 skeleton.

Real bizinfo fetch / persist / attachment download flow lands in commits 2-6
(`docs/.local/feat-ingestion-M2-bizinfo/plan.md`). The worker registers
`ingest_postings` so commit 6 can wire the cron schedule without touching
`apps/worker/stepg_worker/worker.py` again.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def ingest_postings(_ctx: dict[str, Any]) -> None:
    logger.info("ingest_postings placeholder — commit 2-6 wires actual pipeline")


__all__ = ["ingest_postings"]
