"""TAXONOMY.md → in-memory cache for Stage 1 prompt builder + Stage 2 alias remap.

`docs/TAXONOMY.md` (PR #5 머지) is the single source of truth for the 100-node
field-of-work taxonomy. This module reads it once at first access and exposes
four read-only views consumed by:

- Stage 1 prompt builder (M4 commit 4) — `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}`
  placeholder substitution (`docs/PROMPTS.md §2.1`).
- Stage 2 alias remap (M4 commit 5) — LLM-emitted path normalization +
  alias→canonical path lookup (`docs/PROMPTS.md §6` step 1-2).

Both stages read from the same module-level cache so the invariant "Stage 1 and
Stage 2 see the same 100 nodes" holds without DB drift risk (`plan.md` Q2=2).

Lifecycle: lazy load on first access (`_load()` populates a frozen `_CacheState`).
TAXONOMY.md update SOP per `PROMPTS.md §9.1` line 516 = full app restart, so the
single-load cache invalidation is acceptable.

Failure mode: missing or empty TAXONOMY.md raises `RuntimeError` at first
access (fail-fast). Stage 1 LLM accuracy depends on the taxonomy being fully
populated; silent fallback to an empty cache would mask broken state and
produce hallucinated tags downstream.

Alias parsing follows `docs/TAXONOMY.md §3` line 40: take the *last*
paren-balanced block per node line as the alias list, with up to 1-level
nesting. Multi-match tie-break = lexicographically smallest path
(`docs/PROMPTS.md §6` step 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING

from stepg_core.core.config import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping

_TAXONOMY_PATH = REPO_ROOT / "docs" / "TAXONOMY.md"

# §5 / §5.1 / §6 header markers. TAXONOMY.md heading text is hand-curated SoT
# (`PROMPTS.md §9.2` 갱신 빈도 월 1회 미만), so plain regex is stable enough —
# parser dependency (markdown-it-py 등) 도입은 Phase 1.5 (commit 2 Batch B Q16).
_SECTION_5_START = re.compile(r"^## 5\. 트리\s*$", re.MULTILINE)
_SECTION_5_1_START = re.compile(r"^### 5\.1 boundary 우선순위", re.MULTILINE)
_SECTION_6_START = re.compile(r"^## 6\. ", re.MULTILINE)

# Fenced code block (the ASCII tree lives inside one such block within §5).
_FENCE_BLOCK = re.compile(r"^```\s*\n(.*?)\n^```\s*$", re.MULTILINE | re.DOTALL)

# Per-line node header: `[path] name (...)`. Tree-drawing chars + leading
# whitespace stripped before this matches.
_NODE_PATTERN = re.compile(r"^\[([a-z0-9_.]+)\]\s+(.*)$")

# Paren-balanced block (TAXONOMY.md §3 line 40 SoT) — covers up to 1-level
# nesting (e.g. `(창업 초기 (3년 이내), 창업 초기, ...)`).
_PAREN_BLOCK = re.compile(r"\([^()]*(?:\([^()]*\)[^()]*)*\)")


@dataclass(frozen=True)
class _CacheState:
    """Frozen snapshot of TAXONOMY.md views populated on first `_load()` call."""

    tree: str
    boundary: str
    valid_paths: frozenset[str]
    alias_index: Mapping[str, str]


def _read_taxonomy() -> str:
    if not _TAXONOMY_PATH.exists():
        raise RuntimeError(
            f"TAXONOMY.md 미존재 — {_TAXONOMY_PATH}. "
            "Pre-work 1.1 (PR #5)이 머지된 상태인지 확인하세요."
        )
    text = _TAXONOMY_PATH.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"TAXONOMY.md가 비어있음 — {_TAXONOMY_PATH}.")
    return text


def _extract_tree(text: str) -> str:
    """`{TAXONOMY_TREE}` substitute = §5 안 fenced ASCII tree.

    §5 본문은 `## 5. 트리` 헤더 + narrative + ```` ``` ```` fenced block + 통계
    한 줄 + `### 5.1 ...` 헤더 직전까지. 본 함수는 fenced block 내용만 추출
    (LLM이 나레이티브 / 통계 줄을 봐도 도움 안 됨, fenced tree가 SoT).
    """
    s5 = _SECTION_5_START.search(text)
    s51 = _SECTION_5_1_START.search(text)
    if not s5 or not s51:
        raise RuntimeError(
            "TAXONOMY.md '## 5. 트리' 또는 '### 5.1 boundary 우선순위' 헤더 누락 — 파일 양식 확인."
        )
    section_5_body = text[s5.end() : s51.start()]
    fence = _FENCE_BLOCK.search(section_5_body)
    if not fence:
        raise RuntimeError("TAXONOMY.md §5 안 fenced code block 누락 — ASCII 트리 양식 확인.")
    block = fence.group(1).strip()
    if not block:
        raise RuntimeError("TAXONOMY.md §5 fenced 트리가 비어있음.")
    return block


def _extract_boundary(text: str) -> str:
    """`{TAXONOMY_BOUNDARY}` substitute = §5.1 전체 (헤더 포함, 다음 ## 6. 직전).

    §5.1은 (a) overlap 페어 표 + (b) cross-axis bullet + inject 메커니즘 단락.
    LLM은 표·bullet을 그대로 markdown으로 읽음 — 별 변환 없이 원본 보존이 SoT.
    """
    s51 = _SECTION_5_1_START.search(text)
    s6 = _SECTION_6_START.search(text)
    if not s51 or not s6:
        raise RuntimeError(
            "TAXONOMY.md '### 5.1 ...' 또는 다음 섹션 '## 6.' 헤더 누락 — 파일 양식 확인."
        )
    block = text[s51.start() : s6.start()].strip()
    if not block:
        raise RuntimeError("TAXONOMY.md §5.1 boundary 블록이 비어있음.")
    return block


def normalize_alias(s: str) -> str:
    """Stage 2 alias remap normalization — caller 진입점 (`PROMPTS.md §6` step 1).

    `lower().strip()` + 내부 공백을 단일 space로 압축. Stage 2 (M4 commit 5)가
    LLM 출력 path를 본 함수로 정규화한 뒤 `get_alias_index()`로 lookup —
    cache 빌드 정규화와 단일 SoT (dual-implementation 회피).
    """
    return re.sub(r"\s+", " ", s.strip().lower())


def _split_aliases(paren_block_inner: str) -> tuple[str, ...]:
    """Comma-split `paren_block_inner`, depth-aware (1-level 까지).

    Entry like `'창업 초기 (3년 이내), 창업 초기, ...'` 의 nested paren 안 콤마는
    무시하고 outer 콤마만 split. `_parse_aliases` 의 helper.
    """
    aliases: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in paren_block_inner:
        if ch == "," and depth == 0:
            entry = "".join(buf).strip()
            if entry:
                aliases.append(entry)
            buf = []
        else:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            buf.append(ch)
    entry = "".join(buf).strip()
    if entry:
        aliases.append(entry)
    return tuple(aliases)


def _parse_node_line(line: str) -> tuple[str, str, tuple[str, ...]] | None:
    """Strip tree chars + parse `[path] name (aliases) · KSIC: ...` per node.

    Returns `(path, name_body, aliases)` or `None` for non-node lines (blank,
    comments inside the fence, etc.). `name_body`는 alias 마지막 괄호 블록 직전
    까지의 텍스트 — `name`도 alias 후보로 포함된다 (`TAXONOMY.md §3` 정책).
    """
    stripped = line.lstrip(" \t├└│─")
    match = _NODE_PATTERN.match(stripped)
    if not match:
        return None
    path = match.group(1)
    rest = match.group(2)

    # Strip `· KSIC: <codes>` suffix before alias extraction (KSIC tail uses no
    # parens so paren-balanced regex would still work, but explicit split keeps
    # the alias block boundary clean).
    alias_source = rest.split("· KSIC:")[0].strip()

    paren_matches = list(_PAREN_BLOCK.finditer(alias_source))
    if paren_matches:
        last = paren_matches[-1]
        aliases = _split_aliases(last.group(0)[1:-1])
        name_body = alias_source[: last.start()].strip()
    else:
        # Node line with no alias paren block — name only.
        aliases = ()
        name_body = alias_source.strip()

    return path, name_body, aliases


def _build_indexes(tree_block: str) -> tuple[frozenset[str], Mapping[str, str]]:
    """Walk fenced tree → (`valid_paths`, `alias_index`).

    Multi-match tie-break: same normalized alias → N nodes → pick lexicographic-
    smallest path (`PROMPTS.md §6` step 2). `name_body`도 alias 인덱스에 포함된다
    (LLM이 path 또는 display name 둘 다 emit 가능).
    """
    paths: set[str] = set()
    candidates: list[tuple[str, str]] = []

    for raw_line in tree_block.splitlines():
        parsed = _parse_node_line(raw_line)
        if parsed is None:
            continue
        path, name_body, aliases = parsed
        paths.add(path)
        for alias in (*aliases, name_body):
            normalized = normalize_alias(alias)
            if normalized:
                candidates.append((normalized, path))

    by_alias: dict[str, list[str]] = {}
    for alias, path in candidates:
        by_alias.setdefault(alias, []).append(path)
    alias_index = MappingProxyType(
        {alias: min(paths_for_alias) for alias, paths_for_alias in by_alias.items()}
    )

    return frozenset(paths), alias_index


@lru_cache(maxsize=1)
def _load() -> _CacheState:
    """Lazy initialization — first call reads + parses TAXONOMY.md, cached thereafter.

    `lru_cache(maxsize=1)` 가 단일-슬롯 lazy init idiom (`core/config.py::get_settings`
    동일 패턴). 테스트 / 운영 reload 시 `_load.cache_clear()`로 force-reset 가능.
    """
    text = _read_taxonomy()
    tree = _extract_tree(text)
    boundary = _extract_boundary(text)
    valid_paths, alias_index = _build_indexes(tree)
    return _CacheState(
        tree=tree,
        boundary=boundary,
        valid_paths=valid_paths,
        alias_index=alias_index,
    )


def get_taxonomy_tree() -> str:
    """`{TAXONOMY_TREE}` placeholder substitute (`PROMPTS.md §2.1` policy + §3 system prompt).

    Returns the §5 fenced ASCII tree as-is — paths + names + aliases + KSIC
    suffix all preserved per the SoT 양식.
    """
    return _load().tree


def get_taxonomy_boundary() -> str:
    """`{TAXONOMY_BOUNDARY}` placeholder substitute (`PROMPTS.md §2.1` policy + §3 system prompt).

    Returns the §5.1 markdown block as-is — overlap pair table + cross-axis
    bullets + inject 메커니즘 단락 모두 preserved.
    """
    return _load().boundary


def get_valid_paths() -> frozenset[str]:
    """Stage 2 path-exact match input (`PROMPTS.md §6` step 2 (a))."""
    return _load().valid_paths


def get_alias_index() -> Mapping[str, str]:
    """Stage 2 alias remap input (`PROMPTS.md §6` step 2 (b)).

    Keys are normalized via `normalize_alias` (lowercase + collapsed whitespace).
    Values are the canonical taxonomy path (e.g., `'tech.ai_ml.nlp'`).
    Multi-match tie-break = lexicographically smallest path.
    """
    return _load().alias_index


__all__ = [
    "get_alias_index",
    "get_taxonomy_boundary",
    "get_taxonomy_tree",
    "get_valid_paths",
    "normalize_alias",
]
