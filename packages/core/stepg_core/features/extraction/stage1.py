"""Stage 1 — `extract_posting_data` tool 호출.

M4 commit 4 — `docs/PROMPTS.md §1` SDK 호출 양식 mirror. `cache_control: ephemeral`
× 2 (system block + tools[0]) + `tool_choice` 강제 단일 tool + `asyncio.timeout(60.0)`
외층 wrapper (`CLAUDE.md` absolute rule C — timeout + retry 강제 만족; commit 3의
SDK 내장 `max_retries=2`와 dual layer).

호출 결과 = LLM의 `tool_use` block input dict — Stage 2 (commit 5)가 정규화 +
alias remap + Pydantic 검증으로 받음.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from anthropic.types import ToolUseBlock
from stepg_core.core.config import get_settings
from stepg_core.features.extraction.anthropic_client import (
    EXTRACT_POSTING_DATA_TOOL,
    get_anthropic_client,
)
from stepg_core.features.extraction.prompts import build_user_prompt, get_system_prompt

if TYPE_CHECKING:
    from collections.abc import Iterable

    from anthropic.types import ToolParam
    from stepg_core.features.postings.models import Attachment, Posting

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 60.0
"""Outer asyncio timeout. SDK 내장 `max_retries=2`와 dual layer로 CLAUDE.md
absolute rule C 만족."""

_MAX_TOKENS = 4096
"""tool arguments JSON output 한도. 12 + 18 필드 + 신뢰도 dict 평균 1.5K-2.5K
토큰 추정. 4K 여유 공간 — Phase 1.5 prompt tuning 시 재조정."""


async def call_stage1(posting: Posting, attachments: Iterable[Attachment]) -> dict[str, Any]:
    """Stage 1 — Claude Sonnet 4.6 호출 + tool arguments dict 반환.

    `cache_control: ephemeral` 두 곳 박음 — system block (TAXONOMY 100 노드 +
    boundary + 시스템 본문 약 6K 토큰) + tools[0] (extract_posting_data tool desc).
    Anthropic SDK 양식상 system 블록 cache_control이 tool 정의를 cover X 라 두
    cache_control 명시 필수 (`PROMPTS.md §1` line 49).

    `tool_choice` 강제 = LLM이 텍스트 응답 / 다른 tool 호출 모두 차단, 단일
    `extract_posting_data` 만 emit (`PROMPTS.md §3` line 302).

    Stage 2 (commit 5)가 받은 dict를 정규화 + alias remap + Pydantic 검증.
    """
    settings = get_settings()
    client = get_anthropic_client()
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(posting, attachments)

    async with asyncio.timeout(_TIMEOUT_SECONDS):
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                cast(
                    "ToolParam",
                    {**EXTRACT_POSTING_DATA_TOOL, "cache_control": {"type": "ephemeral"}},
                )
            ],
            tool_choice={"type": "tool", "name": EXTRACT_POSTING_DATA_TOOL["name"]},
            messages=[{"role": "user", "content": user_prompt}],
        )

    for block in response.content:
        if isinstance(block, ToolUseBlock) and block.name == EXTRACT_POSTING_DATA_TOOL["name"]:
            # SDK 0.97 type guarantee: `ToolUseBlock.input: dict[str, object]` — isinstance
            # 추가 검사 redundant (`reportUnnecessaryIsInstance`). SDK 가 parse 시점에 dict
            # 양식 강제, tool_choice 강제 + input_schema "type": "object" 와 cross-layer 보장.
            logger.info(
                "Stage 1 ok — posting_id=%d input_tokens=%d output_tokens=%d cache_read=%d",
                posting.id,
                response.usage.input_tokens,
                response.usage.output_tokens,
                response.usage.cache_read_input_tokens or 0,
            )
            return cast("dict[str, Any]", block.input)

    raise RuntimeError(
        f"Stage 1 응답에 extract_posting_data tool_use block 부재 — posting_id={posting.id}"
    )


__all__ = ["call_stage1"]
