"""Section splitter (M3 commit 5 SoT).

Splits a list of paragraphs into a `dict[str, str]` keyed by English
section names (`target` / `support` / `documents` / `eligibility` /
`deadline`) via Korean header regex matching. Returns an empty dict if
no recognized header is found (Q5 best-effort policy — M4 LLM은 전체
텍스트 fallback 사용).

Commit 1 stub — `split_sections` 본문은 commit 5 에서 채움.
"""

from __future__ import annotations


def split_sections(paragraphs: list[str]) -> dict[str, str]:
    raise NotImplementedError("split_sections — commit 5에서 구현")


__all__ = ["split_sections"]
