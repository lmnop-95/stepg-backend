"""Stage 2 — LLM 출력 정규화 + alias remap + invalid 로깅 + Pydantic 검증.

`docs/PROMPTS.md §6` SoT mirror. 5 step 순서 의존:

1. **입력 normalize**: `field_of_work_tag_ids` 각 element `taxonomy_cache.normalize_alias`
   적용 (lower + 공백 압축). `tag_confidence_per_id` 키도 같은 함수로 정규화.
2. **alias remap**: 정규화 후 (a) `_VALID_PATHS` path-exact → (b) `_ALIAS_INDEX`
   alias-exact → (c) miss → invalid drop. multi-match tie-break = 사전순 (cache
   빌드 시 결정성).
3. **invalid 로깅**: `STAGE2_INVALID_TAG` audit row 빌드 (DB insert는 commit 7
   service의 단일 transaction 안 — `actor_user_id=null` system actor).
4. **final dict 정합**: `tag_confidence_per_id` 키를 valid `field_of_work_tag_ids`
   와 동기화 — invalid 제거된 path 의 신뢰도 키도 함께 제거.
5. **eligibility 검증**: Pydantic `EligibilityRules` model_validate. 실패 시 per-field
   fallback (`STAGE2_INVALID_FIELD` audit row) — nullable list/int 필드 → null,
   `prior_recipients_excluded` → False, `free_text_conditions` → []. `field_confidence_scores`
   는 변경 X (LLM 원본 보존, `PROMPTS.md §6` step 5).

Stage 3 (commit 6)가 `Stage2Result` 받아 분기 룰 입력으로 사용. audit_rows는
commit 7 service의 단일 transaction 안 적재 (Q29=1 — pure logic, DB write X).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from stepg_core.features.extraction.schemas import EligibilityRules, ExtractedPostingData
from stepg_core.features.extraction.taxonomy_cache import (
    get_alias_index,
    get_valid_paths,
    normalize_alias,
)

# Audit action constants — `features/review/models.py::AUDIT_ACTIONS` (M1 schema +
# 마이그레이션 0013) SoT 인용. DB CHECK constraint 가 invalid 적재 시점에 강제 — 본 코드
# 는 row 빌더 양식 mirror.
_AUDIT_INVALID_TAG = "STAGE2_INVALID_TAG"
_AUDIT_INVALID_FIELD = "STAGE2_INVALID_FIELD"

# `PROMPTS.md §6` step 5 — eligibility 18 필드 type별 fallback. 16 nullable 필드는
# null, 2 non-nullable은 type default (`prior_recipients_excluded=False`,
# `free_text_conditions=[]`). 미명시 필드는 `_NULLABLE_FALLBACK` 로 처리.
_FIELD_FALLBACKS: dict[str, Any] = {
    "prior_recipients_excluded": False,
    "free_text_conditions": [],
}
_NULLABLE_FALLBACK: Any = None


@dataclass(frozen=True)
class Stage2Result:
    """Stage 2 출력 — Stage 3 (commit 6) + 적재 (commit 7) 입력.

    `extracted` = `ExtractedPostingData` Pydantic instance (eligibility nested
    포함). `audit_rows` = 단일 transaction 안 적재될 `ExtractionAuditLog` payload
    list (commit 7 service 책임). frozen — Stage 3 / 적재 전 수정 차단.
    """

    extracted: ExtractedPostingData
    audit_rows: tuple[dict[str, Any], ...]


def _build_invalid_tag_row(
    posting_id: int,
    raw_path: str,
    normalized: str,
    confidence: float | None,
) -> dict[str, Any]:
    """`STAGE2_INVALID_TAG` audit row 양식 (`PROMPTS.md §6` step 3 SoT).

    `before` = LLM 원본 raw_path + 신뢰도, `after` = drop 사유 + normalized + matched_node
    null. `actor_user_id` = null (system actor — `PROMPTS.md §6` step 3 + ExtractionAuditLog
    docstring case (b) 일관).
    """
    return {
        "posting_id": posting_id,
        "action": _AUDIT_INVALID_TAG,
        "before": {"raw_path": raw_path, "confidence": confidence},
        "after": {
            "reason": "invalid_tag_dropped",
            "normalized": normalized,
            "matched_node": None,
        },
        "actor_user_id": None,
    }


def _build_invalid_field_row(
    posting_id: int,
    field_name: str,
    raw_value: Any,
    fallback_value: Any,
    error_messages: list[str],
) -> dict[str, Any]:
    """`STAGE2_INVALID_FIELD` audit row 양식 (`PROMPTS.md §6` step 5 SoT).

    Pydantic schema 위반 (type / enum / KSIC custom validator) 시 emit. `before` =
    LLM 원본 raw_value + Pydantic error messages, `after` = fallback 치환값.
    """
    return {
        "posting_id": posting_id,
        "action": _AUDIT_INVALID_FIELD,
        "before": {
            "field": field_name,
            "raw_value": raw_value,
            "errors": error_messages,
        },
        "after": {
            "reason": "invalid_field_fallback",
            "fallback_value": fallback_value,
        },
        "actor_user_id": None,
    }


def _remap_tags(
    raw_tags: list[str],
    raw_confidence: dict[str, float],
    posting_id: int,
) -> tuple[list[str], dict[str, float], list[dict[str, Any]]]:
    """`PROMPTS.md §6` step 1-4 — normalize + alias remap + invalid drop + 키 sync.

    Single-pass over `raw_tags`로 3 outputs 동시 빌드:
    - `valid_tag_ids`: dedupe canonical paths preserving first-occurrence order.
    - `valid_confidence`: canonical → max confidence (multi raw → 동일 canonical 시
      max 채택, LLM 자기평가 confident 발신 보존; plan.md commit 5 본문 SoT).
    - `audit_rows`: invalid drop별 `STAGE2_INVALID_TAG` payload.
    """
    valid_paths = get_valid_paths()
    alias_index = get_alias_index()
    valid_tag_ids: list[str] = []
    valid_confidence: dict[str, float] = {}
    audit_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw_tag in raw_tags:
        normalized = normalize_alias(raw_tag)
        if normalized in valid_paths:
            canonical = normalized
        elif normalized in alias_index:
            canonical = alias_index[normalized]
        else:
            audit_rows.append(
                _build_invalid_tag_row(
                    posting_id=posting_id,
                    raw_path=raw_tag,
                    normalized=normalized,
                    confidence=_safe_float(raw_confidence.get(raw_tag)),
                )
            )
            continue

        if canonical not in seen:
            valid_tag_ids.append(canonical)
            seen.add(canonical)

        conf = _safe_float(raw_confidence.get(raw_tag))
        if conf is not None and 0 <= conf <= 1:
            valid_confidence[canonical] = max(valid_confidence.get(canonical, 0.0), conf)

    return valid_tag_ids, valid_confidence, audit_rows


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _validate_eligibility(
    raw: dict[str, Any],
    posting_id: int,
) -> tuple[EligibilityRules, list[dict[str, Any]]]:
    """`PROMPTS.md §6` step 5 — Pydantic 검증 + per-field fallback.

    1차 model_validate 성공 시 그대로 반환. 실패 시 ValidationError에서 실패 필드
    추출 → per-field fallback 치환 → 재검증. 재검증 실패는 raise (Pydantic schema
    구조 자체 위반 — LLM이 dict 가 아닌 양식 emit 등 비정상).
    """
    try:
        return EligibilityRules.model_validate(raw), []
    except ValidationError as e:
        first_pass_errors = e.errors()

    audit_rows: list[dict[str, Any]] = []
    cleaned: dict[str, Any] = dict(raw)

    # ValidationError loc[0] = 필드명 (또는 nested item index loc[1]). 동일 필드의
    # 여러 error를 그룹핑해서 한 audit row로 통합.
    errors_by_field: dict[str, list[str]] = {}
    for err in first_pass_errors:
        loc = err.get("loc") or ()
        if not loc:
            continue
        field_name = str(loc[0])
        if field_name not in EligibilityRules.model_fields:
            continue
        errors_by_field.setdefault(field_name, []).append(err.get("msg", ""))

    for field_name, error_messages in errors_by_field.items():
        raw_value = cleaned.get(field_name)
        fallback = _FIELD_FALLBACKS.get(field_name, _NULLABLE_FALLBACK)
        cleaned[field_name] = fallback
        audit_rows.append(
            _build_invalid_field_row(
                posting_id=posting_id,
                field_name=field_name,
                raw_value=raw_value,
                fallback_value=fallback,
                error_messages=error_messages,
            )
        )

    return EligibilityRules.model_validate(cleaned), audit_rows


def validate_stage1_output(posting_id: int, raw: dict[str, Any]) -> Stage2Result:
    """Stage 2 entry — LLM Stage 1 출력 dict → 검증된 `Stage2Result`.

    입력 `raw` = `stage1.call_stage1` 반환 (Anthropic SDK `ToolUseBlock.input`).
    출력 `Stage2Result.extracted` = 12 + 18 필드 검증된 Pydantic instance,
    `audit_rows` = 단일 tx 적재될 audit payload (commit 7 service 책임).

    eligibility 외 11 top-level 필드는 Pydantic 직 검증 (LLM이 tool input_schema
    enum 강제로 emit, 위반 시 raise — Phase 1 fail-fast SOP).
    """
    audit_rows: list[dict[str, Any]] = []

    raw_tags = list(raw.get("field_of_work_tag_ids") or [])
    raw_confidence = dict(raw.get("tag_confidence_per_id") or {})
    valid_tags, valid_confidence, tag_audit_rows = _remap_tags(
        raw_tags=raw_tags,
        raw_confidence=raw_confidence,
        posting_id=posting_id,
    )
    audit_rows.extend(tag_audit_rows)

    raw_eligibility = dict(raw.get("eligibility") or {})
    eligibility, field_audit_rows = _validate_eligibility(
        raw=raw_eligibility,
        posting_id=posting_id,
    )
    audit_rows.extend(field_audit_rows)

    extracted = ExtractedPostingData.model_validate(
        {
            "eligibility": eligibility,
            "field_of_work_tag_ids": valid_tags,
            "tag_confidence_per_id": valid_confidence,
            "funding_uses": raw.get("funding_uses") or [],
            "support_amount_min": raw.get("support_amount_min"),
            "support_amount_max": raw.get("support_amount_max"),
            "deadline_precise": raw.get("deadline_precise"),
            "required_documents": raw.get("required_documents") or [],
            "field_confidence_scores": raw.get("field_confidence_scores") or {},
            "summary": raw.get("summary") or "",
            "target_description": raw.get("target_description") or "",
            "support_description": raw.get("support_description") or "",
        }
    )

    return Stage2Result(extracted=extracted, audit_rows=tuple(audit_rows))


__all__ = ["Stage2Result", "validate_stage1_output"]
