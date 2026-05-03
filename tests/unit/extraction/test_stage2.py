"""Stage 2 alias remap + invalid 로깅 unit test (`PROMPTS.md §8.4` SoT cross-ref).

F4 (iii) 적용 (M4.4 commit 1) — `tests/integration/extraction/test_golden.py::test_golden_8_4_invalid_trigger`
폐기 후 본 unit test 로 대체. real Anthropic API + LLM 환각 의존 제거 → cost $0 + 재현성 ↑.

cover (`PROMPTS.md §6` step 1-3 본질):
- (a) path-exact match — canonical path 입력 → valid, `audit_rows` empty
- (b) alias-list match — alias 입력 → canonical remap, `audit_rows` empty
- (c) invalid (path + alias miss) → invalid drop + `STAGE2_INVALID_TAG` audit row 1건
"""

from __future__ import annotations

from typing import Any, Final

from stepg_core.features.extraction.stage2 import (
    AUDIT_INVALID_TAG,
    validate_stage1_output,
)
from stepg_core.features.extraction.taxonomy_cache import (
    get_alias_index,
    get_valid_paths,
)

# audit row echo 검증용 placeholder — production posting_id 와 무관 (DB 적재 X).
_POSTING_ID: Final[int] = 1
# LLM 환각 path (TAXONOMY.md §5 부재) — invalid drop 검증용.
_INVALID_PATH: Final[str] = "tech.quantum.computing"
# TAXONOMY.md §5 root umbrella — 변경 시 fixture 갱신 mandate.
_CANONICAL_PATH: Final[str] = "tech.ai_ml"
# `tech.ai_ml` alias (normalize 후 "ai/ml") — TAXONOMY.md §5 SoT.
_ALIAS_PATH: Final[str] = "AI/ML"


def _minimal_valid_raw() -> dict[str, Any]:
    """`PROMPTS.md §1` 12 top-level 필드 minimal valid raw.

    `field_of_work_tag_ids` + `tag_confidence_per_id` 만 test 별 override.
    """
    return {
        "eligibility": {},
        "field_of_work_tag_ids": [],
        "tag_confidence_per_id": {},
        "funding_uses": [],
        "support_amount_min": None,
        "support_amount_max": None,
        "deadline_precise": None,
        "required_documents": [],
        "field_confidence_scores": {},
        "summary": "",
        "target_description": "",
        "support_description": "",
    }


def test_stage2_path_exact_match() -> None:
    raw = _minimal_valid_raw()
    raw["field_of_work_tag_ids"] = [_CANONICAL_PATH]
    raw["tag_confidence_per_id"] = {_CANONICAL_PATH: 0.9}

    result = validate_stage1_output(_POSTING_ID, raw)

    assert result.extracted.field_of_work_tag_ids == [_CANONICAL_PATH]
    assert result.extracted.tag_confidence_per_id == {_CANONICAL_PATH: 0.9}
    assert result.audit_rows == ()


def test_stage2_alias_remap() -> None:
    raw = _minimal_valid_raw()
    raw["field_of_work_tag_ids"] = [_ALIAS_PATH]
    raw["tag_confidence_per_id"] = {_ALIAS_PATH: 0.8}

    result = validate_stage1_output(_POSTING_ID, raw)

    assert result.extracted.field_of_work_tag_ids == [_CANONICAL_PATH]
    assert result.extracted.tag_confidence_per_id == {_CANONICAL_PATH: 0.8}
    assert result.audit_rows == ()


def test_stage2_invalid_drop() -> None:
    valid_paths = get_valid_paths()
    alias_index = get_alias_index()
    assert _INVALID_PATH not in valid_paths
    assert _INVALID_PATH not in alias_index

    raw = _minimal_valid_raw()
    raw["field_of_work_tag_ids"] = [_INVALID_PATH]
    raw["tag_confidence_per_id"] = {_INVALID_PATH: 0.5}

    result = validate_stage1_output(_POSTING_ID, raw)

    assert result.extracted.field_of_work_tag_ids == []
    assert result.extracted.tag_confidence_per_id == {}
    assert len(result.audit_rows) == 1
    audit = result.audit_rows[0]
    assert audit["action"] == AUDIT_INVALID_TAG
    assert audit["posting_id"] == _POSTING_ID
    assert audit["actor_user_id"] is None
    assert audit["before"]["raw_path"] == _INVALID_PATH
    assert audit["before"]["confidence"] == 0.5
    assert audit["after"]["normalized"] == _INVALID_PATH
    assert audit["after"]["matched_node"] is None
