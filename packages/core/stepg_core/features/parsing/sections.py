"""Section splitter (M3 commit 5).

Splits a list of paragraphs into a `dict[str, str]` keyed by English
section names (`target` / `support` / `documents` / `eligibility` /
`deadline`) via Korean header regex matching. Returns an empty dict if
no recognized header is found (Q5 best-effort policy — M4 LLM은 전체
텍스트 fallback 사용).

매칭 단위는 paragraph 첫 줄 (Q47): HWPX `preserve_breaks=True` 로
paragraph 안 `\\n` 이 보존되므로 합본 paragraph (`지원대상\\n중소기업...`)도
첫 줄로 헤더 검출. **trade-off**: paragraph 안 둘째+ 줄에 헤더가 등장하면
손실 (Q5 best-effort 정책 일관 — 정부 공고 헤더는 일반적으로 paragraph
시작에 위치, false negative 비율 낮음). 번호 / bullet prefix 허용 (Q50):
`1. 지원대상`, `① 지원대상`, `□ 지원대상` 형태. 한글 한정사 (`세부`,
`상세`, `주요`, `핵심`) prefix 도 허용 — 정부 공고 흔한 `3. 세부 지원내용`
패턴 대응. 헤더 line 뒤 콜론 + inline body 가 있으면 그 부분도 본문에
포함 (`□ 지원대상: 중소기업기본법 제2조...`). 헤더 line 자체는 본문 제외
(Q53). 같은 키 중복 등장 시 첫 등장만 채움 (Q52) — 후속은 부록 가정.
"""

from __future__ import annotations

import re
from typing import Final

# 보수적 별칭 사전 (Q49) — 정부 공고 90% 커버. false match 회피 위해
# `지원개요` 같은 모호 헤더 제외. `지원규모` (≠ "지원내용", 금액 규모는
# 별개 정보) / `사업기간` (≠ "신청기간", project duration ≠ application
# window) 도 제거 — M3→M4 contract (`Posting.support_description`,
# `deadline_at`) 정확도 보호 (Q56).
_HEADER_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "target": ("지원대상", "지원 대상", "신청대상", "신청 대상"),
    "support": ("지원내용", "지원 내용", "지원사업 내용"),
    "documents": ("제출서류", "제출 서류", "구비서류", "신청서류"),
    "eligibility": ("신청자격", "신청 자격", "참여자격", "지원자격"),
    "deadline": ("신청기간", "접수기간", "마감일", "신청마감"),
}

SECTION_KEYS: Final[tuple[str, ...]] = tuple(_HEADER_ALIASES.keys())
"""5 키 SoT — `_HEADER_ALIASES` derive. M4 prompt builder
(`features/extraction/prompts.py`)가 LLM reading 양식 (`target → support →
documents → eligibility → deadline` 순서) 으로 import — 본 모듈 SoT 단일."""

# 번호 / bullet prefix 허용 (Q50): 숫자 (`1.`, `1)`), 한글 동그라미
# (`①`-`⑩`), 일반 bullet (`□`, `○`, `●`, `■`, `▶`, `◇`, `◆`, `※`).
_BULLET_PREFIX = r"[-\d①-⑩.)\s□○●■▶◇◆※·]*"

# 한글 한정사 prefix — `3. 세부 지원내용` 같은 정부 공고 흔한 패턴.
_QUALIFIER_PREFIX = r"(?:세부|상세|주요|핵심)?\s*"

# 키별 컴파일된 헤더 regex.
# 매칭 형태:
#   `<bullet><qualifier><alias>` — 헤더 own line, body 다음 paragraph 부터.
#   `<bullet><qualifier><alias>:<inline body>` — 헤더 + 콜론 + inline body.
# group 1 = inline body (콜론 뒤). 콜론 자체 optional.
_HEADER_REGEXES: Final[dict[str, re.Pattern[str]]] = {
    key: re.compile(
        r"^\s*"
        + _BULLET_PREFIX
        + _QUALIFIER_PREFIX
        + r"(?:"
        + "|".join(re.escape(a) for a in aliases)
        + r")\s*(?:[:：]\s*(.*?))?\s*$"
    )
    for key, aliases in _HEADER_ALIASES.items()
}


def _match_header(line: str) -> tuple[str, str] | None:
    # 반환: (key, inline_body) — inline_body 는 콜론 뒤 본문 (없으면 빈 문자열).
    for key, pattern in _HEADER_REGEXES.items():
        m = pattern.match(line)
        if m is not None:
            return key, (m.group(1) or "").strip()
    return None


def split_sections(paragraphs: list[str]) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    current_buffer: list[str] = []

    def flush() -> None:
        # 첫 등장만 채움 (Q52). 같은 키 중복 시 후속 무시. 빈 buffer는
        # 두 헤더 연속 매칭 등으로 발생 가능 — 의도 한 곳(이 가드)에 모음.
        if current_key is not None and current_buffer and current_key not in sections:
            sections[current_key] = list(current_buffer)

    for paragraph in paragraphs:
        # paragraph 안 `\n` line-by-line 검사 (Q47). 헤더 만나면 paragraph 를
        # 헤더-전 / 헤더-라인 / 헤더-후 로 split. 헤더 라인 자체는 본문 제외 (Q53),
        # but 콜론 뒤 inline body 는 본문에 포함.
        lines = paragraph.split("\n")
        first_stripped = lines[0].strip()
        match = _match_header(first_stripped)
        if match is not None:
            matched_key, inline_body = match
            flush()
            current_key = matched_key
            current_buffer = []
            if inline_body:
                current_buffer.append(inline_body)
            remainder = "\n".join(lines[1:]).strip()
            if remainder:
                current_buffer.append(remainder)
        elif current_key is not None:
            current_buffer.append(paragraph)

    flush()
    return {key: "\n\n".join(buf) for key, buf in sections.items()}


__all__ = ["SECTION_KEYS", "split_sections"]
