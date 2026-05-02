"""Stage 1 prompt builders — system + user prompt SoT mirror.

M4 commit 4 — `docs/PROMPTS.md §3` 시스템 prompt + `§4` 유저 prompt 양식 mirror.

System prompt: PROMPTS.md §3 의 fenced text를 startup 1회 read + cache.
호출 시 `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` 두 placeholder만 `str.replace()`
substitute (`PROMPTS.md §2.1` MUST 룰). `{POSTING_BODY}` / `{ATTACHMENT_TEXT}` /
`{POSTING_META}` literal은 system 안 documentation reference로 보존 — user
message에서 동적 바인딩.

User prompt: PROMPTS.md §4 양식 (`공고:` / `첨부:` / `메타:` 한국어 marker) 따라
3 placeholder 동적 substitute. `{POSTING_BODY}` = `Posting.raw_payload['bsnsSumryCn']`
HTML→text + `parsing.sections.split_sections()` 5-key concat + 2K chars head
cutoff. `{ATTACHMENT_TEXT}` = `Attachment.sections` 5-key concat per attachment
+ `---` join + 5K chars head + 2K chars tail. `{POSTING_META}` = 수집일 / 마감일 /
소관부처 3 line.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from stepg_core.core.config import REPO_ROOT
from stepg_core.features.extraction.taxonomy_cache import (
    get_taxonomy_boundary,
    get_taxonomy_tree,
)
from stepg_core.features.parsing.sections import SECTION_KEYS, split_sections

if TYPE_CHECKING:
    from collections.abc import Iterable

    from stepg_core.features.postings.models import Attachment, Posting


_PROMPTS_PATH = REPO_ROOT / "docs" / "PROMPTS.md"

# §3 fenced text 경계 — 갱신 빈도 월 1회 미만 (`PROMPTS.md §9.2`)이라 plain regex 안전.
_SECTION_3_START = re.compile(r"^## 3\. 시스템 prompt\s*$", re.MULTILINE)
_SECTION_4_START = re.compile(r"^## 4\. 유저 prompt 양식\s*$", re.MULTILINE)
_FENCE_TEXT_BLOCK = re.compile(r"^```text\s*\n(.*?)\n^```\s*$", re.MULTILINE | re.DOTALL)

# Cutoff 정책 (`PROMPTS.md §2` line 259-260 SoT). 한국어 chars 단위 — token이 아닌
# char count 기반 단순 cut. PROMPTS.md SoT 갱신 시 본 상수도 동기 갱신.
_POSTING_BODY_HEAD_CHARS = 2000
_ATTACHMENT_TEXT_HEAD_CHARS = 5000
_ATTACHMENT_TEXT_TAIL_CHARS = 2000

# 5 키 한국어 label mapping — system prompt `## 입력` 한국어 reference 일관
# (`PROMPTS.md §3` line 297). LLM reading 자연성 ↑ (정부 공고 도메인 한국어 marker).
_SECTION_LABELS: dict[str, str] = {
    "target": "지원대상",
    "support": "지원내용",
    "documents": "제출서류",
    "eligibility": "신청자격",
    "deadline": "신청기간",
}

# 한국 정부 공고 자연 reading timezone — DB UTC ↔ LLM 입력 KST 분리
# (CLAUDE.md absolute rule A는 DB 컬럼 강제, LLM 입력 양식은 별 영역).
_KST = ZoneInfo("Asia/Seoul")


def _read_prompts() -> str:
    if not _PROMPTS_PATH.exists():
        raise RuntimeError(
            f"PROMPTS.md 미존재 — {_PROMPTS_PATH}. "
            "Pre-work 1.2 (PR #6)이 머지된 상태인지 확인하세요."
        )
    text = _PROMPTS_PATH.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"PROMPTS.md가 비어있음 — {_PROMPTS_PATH}.")
    return text


def _extract_system_prompt(text: str) -> str:
    """`## 3. 시스템 prompt` 안 ```text fenced block 추출.

    §3 본문은 narrative 1단락 + fenced text 블록 + post-fence narrative. 본 함수는
    fenced block 내용만 추출 (LLM 입력 = fenced text 그대로, narrative는 reader-meta).
    """
    s3 = _SECTION_3_START.search(text)
    s4 = _SECTION_4_START.search(text)
    if not s3 or not s4:
        raise RuntimeError(
            "PROMPTS.md '## 3. 시스템 prompt' 또는 '## 4. ...' 헤더 누락 — 양식 확인."
        )
    section_3_body = text[s3.end() : s4.start()]
    fence = _FENCE_TEXT_BLOCK.search(section_3_body)
    if not fence:
        raise RuntimeError("PROMPTS.md §3 안 fenced text 블록 누락 — 양식 확인.")
    return fence.group(1).strip()


@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """`PROMPTS.md §3` SoT + `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` substitute.

    `str.replace()` 두 키만 substitute (`PROMPTS.md §2.1` MUST 룰). `{POSTING_*}`
    literal은 documentation reference로 보존 — user message에서 동적 바인딩.

    Lazy load + `lru_cache(maxsize=1)` — 운영 중 PROMPTS.md / TAXONOMY.md 갱신 SOP
    = 앱 재시작 (`PROMPTS.md §9.1` line 516).
    """
    template = _extract_system_prompt(_read_prompts())
    return template.replace("{TAXONOMY_TREE}", get_taxonomy_tree()).replace(
        "{TAXONOMY_BOUNDARY}", get_taxonomy_boundary()
    )


def _strip_html(html: str) -> str:
    """`BeautifulSoup.get_text(separator='\n\n')` — HTML 마크업 제거 + entity decode.

    bizinfo `bsnsSumryCn`이 정부 API 관행상 HTML markup 포함 가능 (`<p>...</p>` 등) +
    entity (`&nbsp;` / `&amp;`) 도 decode. `separator='\n\n'`은 block-level element
    사이만 박혀 paragraph 의도 회복 (M3 split_sections paragraph 단위 입력 SoT 일관).
    """
    return BeautifulSoup(html, "html.parser").get_text(separator="\n\n")


def _format_sections(sections: dict[str, str]) -> str:
    """5 key dict → markdown-style concat (Stage 1 LLM reading 양식).

    빈 값 키는 skip — 5 키 모두 빈 경우 빈 문자열 반환 (caller가 fallback 결정).
    키 순서는 `SECTION_KEYS` (M3 SoT) 고정 — LLM이 `지원대상 → 지원내용 → 제출서류
    → 신청자격 → 신청기간` 순서로 reading. label은 한국어 (`_SECTION_LABELS`)
    — system prompt `## 입력` 한국어 reference 일관.
    """
    parts: list[str] = []
    for key in SECTION_KEYS:
        value = sections.get(key, "").strip()
        if value:
            parts.append(f"[{_SECTION_LABELS[key]}]\n{value}")
    return "\n\n".join(parts)


def _build_posting_body(posting: Posting) -> str:
    """`{POSTING_BODY}` substitute (`PROMPTS.md §2`).

    `Posting.raw_payload['bsnsSumryCn']` HTML→text 정규화 → paragraphs split →
    `parsing.sections.split_sections()` 5-key concat → 2K chars head cutoff.
    5 키 모두 미검출 시 plain text 그대로 동일 cutoff fallback (split_sections
    best-effort 정책 일관, M3 패턴).
    """
    raw_payload = posting.raw_payload or {}
    bsns_summary = raw_payload.get("bsnsSumryCn", "")
    if not isinstance(bsns_summary, str) or not bsns_summary.strip():
        return ""
    plain_text = _strip_html(bsns_summary)
    paragraphs = [p.strip() for p in plain_text.split("\n\n") if p.strip()]
    sections = split_sections(paragraphs)
    formatted = _format_sections(sections)
    if not formatted:
        # 5 키 미검출 fallback — raw plain text 그대로.
        formatted = plain_text.strip()
    return formatted[:_POSTING_BODY_HEAD_CHARS]


def _build_attachment_text(attachments: Iterable[Attachment]) -> str:
    """`{ATTACHMENT_TEXT}` substitute (`PROMPTS.md §2`).

    각 첨부의 `Attachment.sections` (M3 산출 dict, 재 split X) 5-key concat →
    첨부 간 `---` separator → 5K chars head + 2K chars tail cutoff. `Attachment.sections`
    빈 attachment 는 `Attachment.extracted_text` raw fallback.

    head + tail cutoff 사이 텍스트는 `[... 중간 생략 ...]` marker로 표시 — LLM
    측 reading 손실 신호 명시.
    """
    parts: list[str] = []
    for attachment in attachments:
        if attachment.sections:
            formatted = _format_sections(attachment.sections)
            if formatted:
                parts.append(formatted)
                continue
        if attachment.extracted_text:
            parts.append(attachment.extracted_text.strip())

    joined = "\n\n---\n\n".join(parts)
    if len(joined) <= _ATTACHMENT_TEXT_HEAD_CHARS + _ATTACHMENT_TEXT_TAIL_CHARS:
        return joined
    head = joined[:_ATTACHMENT_TEXT_HEAD_CHARS]
    tail = joined[-_ATTACHMENT_TEXT_TAIL_CHARS:]
    return f"{head}\n\n[... 중간 생략 ...]\n\n{tail}"


def _build_posting_meta(posting: Posting) -> str:
    """`{POSTING_META}` substitute (`PROMPTS.md §2`).

    3 line: `수집일: <ISO 8601 KST created_at>` / `마감일: <ISO 8601 KST deadline_at,
    null 시 raw_payload reqstBeginEndDe fallback + 빈 시 '미명시' literal>` /
    `소관부처: <jrsdInsttNm, 빈 시 '미명시' literal>`.

    timezone = KST (`+09:00`) — DB는 UTC (CLAUDE.md absolute rule A) 이지만 LLM
    입력 양식은 정부 공고 자연 reading 일관 (`_KST` SoT).
    bizinfo `reqstBeginEndDe`은 한글 자유서술 가능 (`상시 접수`, `예산 소진시까지`)
    → ISO 8601 parse 실패 시 raw 문자열 그대로 LLM에 전달.
    """
    raw_payload = posting.raw_payload or {}

    created_iso = posting.created_at.astimezone(_KST).isoformat()

    if posting.deadline_at:
        deadline_iso = posting.deadline_at.astimezone(_KST).isoformat()
    else:
        deadline_str = raw_payload.get("reqstBeginEndDe")
        deadline_iso = (
            deadline_str if isinstance(deadline_str, str) and deadline_str.strip() else "미명시"
        )

    agency = raw_payload.get("jrsdInsttNm")
    agency_str = agency if isinstance(agency, str) and agency.strip() else "미명시"

    return f"수집일: {created_iso}\n마감일: {deadline_iso}\n소관부처: {agency_str}"


def build_user_prompt(posting: Posting, attachments: Iterable[Attachment]) -> str:
    """`PROMPTS.md §4` 양식 mirror — 3 placeholder substitute 후 user message string.

    `공고:` / `첨부:` / `메타:` 한국어 marker + `\n\n` separator. 본문 → 첨부 → 메타
    reading order (`PROMPTS.md §4` line 357 SoT — 정부 공고 reading order: 본문이
    1차 추출 source, 첨부는 보강, 메타는 보조).
    """
    body = _build_posting_body(posting)
    attachment_text = _build_attachment_text(attachments)
    meta = _build_posting_meta(posting)
    return f"공고:\n{body}\n\n첨부:\n{attachment_text}\n\n메타:\n{meta}"


__all__ = ["build_user_prompt", "get_system_prompt"]
