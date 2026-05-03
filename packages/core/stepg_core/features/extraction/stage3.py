"""Stage 3 — 신뢰도 분기 pure function (`docs/PROMPTS.md §7` SoT).

4 조건 boolean OR — 어느 하나라도 참이면 `needs_review=True`:

- **invalid 태그 존재** ≥ 1개 — Stage 2 `STAGE2_INVALID_TAG` audit row 카운트
  (`PROMPTS.md §7` line 401, ARCHITECTURE.md §5 line 238 SoT). LLM 환각 / 택소노미
  누락 노드 신호 → 큐레이터 검수 시 alias 보강 후보.
- **low-conf 태그 카운트** > 2개 (3개 이상) — `tag_confidence_per_id`의 < 0.7 값
  카운트 (`PROMPTS.md §7` line 402, ARCHITECTURE.md §5 line 239 SoT). 매칭 정확도
  위협 — 다수 path가 추론·모호 zone이면 M6 matching 신뢰도 ↓.
- **low-conf eligibility 필드 카운트** > 2개 (3개 이상) — `field_confidence_scores`의
  < 0.7 값 카운트 (`PROMPTS.md §7` line 403, ARCHITECTURE.md §5 line 240 SoT). Hard
  Filter 입력 신뢰도 위협 — Layer A의 match precision 위협.
- **valid 태그 0개** — Stage 2 final `field_of_work_tag_ids` 빈 배열 (`PROMPTS.md §7`
  line 404, ARCHITECTURE.md §5 line 241 SoT). 매칭 자체 불가능 (Layer B Tag Match
  입력 부재).

Pure function — DB write X. commit 7 service가 `Stage3Decision`을 받아 단일
transaction 안 `ReviewQueueItem` (needs_review=True 시) + `Posting.needs_review`
적재. `reasons`는 `ReviewQueueItem.reasons: list[str]` 컬럼에 한국어 + 카운트
포함 string으로 박혀 M9 admin queue 화면에 직접 노출.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from stepg_core.features.extraction.stage2 import AUDIT_INVALID_TAG

if TYPE_CHECKING:
    from stepg_core.features.extraction.stage2 import Stage2Result

# `PROMPTS.md §5` line 373 (boundary 양식) + line 377 (low-conf 정의) — `< 0.7`
# strict half-open. 정확히 0.7 = 확실 zone (high-conf, low-conf 카운트 미포함).
_LOW_CONF_THRESHOLD = 0.7

# `PROMPTS.md §7` line 400-401 — "low-conf > 2개 (3개 이상)". strict greater-than.
_LOW_CONF_COUNT_THRESHOLD = 2

# Stage 2가 빌드한 audit row의 `action` 키 — `stage2.AUDIT_INVALID_TAG` 가 SoT,
# 본 모듈은 import으로 단일 SoT 유지 (Pass 6 critic F3 dual SoT 회피).


@dataclass(frozen=True)
class Stage3Decision:
    """Stage 3 분기 결과 — `Stage2Result` 받아 `needs_review` + `reasons` return.

    `reasons` = `ReviewQueueItem.reasons: list[str]` 컬럼에 그대로 적재될 한국어
    + 카운트 포함 string list. M9 admin queue 화면에 직접 노출. `needs_review=False`
    시 빈 tuple. frozen — 적재 전 수정 차단.
    """

    needs_review: bool
    reasons: tuple[str, ...]


def evaluate_stage3(stage2_result: Stage2Result) -> Stage3Decision:
    """`PROMPTS.md §7` 4 조건 boolean OR 분기 — pure function.

    어느 한 조건이라도 참이면 `needs_review=True`. 각 조건의 한국어 reason이
    `Stage3Decision.reasons` tuple에 박혀 M9 admin queue 화면에 표시.

    DB write 책임 X — commit 7 service가 `Posting.needs_review` + (분기 시)
    `ReviewQueueItem` 적재 + (auto-approve 시) `AUTO_APPROVE` audit row 적재를
    단일 transaction으로 처리.
    """
    extracted = stage2_result.extracted
    audit_rows = stage2_result.audit_rows

    invalid_tag_count = sum(1 for row in audit_rows if row.get("action") == AUDIT_INVALID_TAG)
    low_conf_tag_count = sum(
        1 for c in extracted.tag_confidence_per_id.values() if c < _LOW_CONF_THRESHOLD
    )
    low_conf_field_count = sum(
        1 for c in extracted.field_confidence_scores.values() if c < _LOW_CONF_THRESHOLD
    )
    valid_tag_count = len(extracted.field_of_work_tag_ids)

    reasons: list[str] = []
    if invalid_tag_count >= 1:
        reasons.append(f"유효하지 않은 태그 {invalid_tag_count}건 검출")
    if low_conf_tag_count > _LOW_CONF_COUNT_THRESHOLD:
        reasons.append(
            f"저신뢰 태그 {low_conf_tag_count}건 "
            f"(>{_LOW_CONF_COUNT_THRESHOLD} 임계, <{_LOW_CONF_THRESHOLD} 신뢰도)"
        )
    if low_conf_field_count > _LOW_CONF_COUNT_THRESHOLD:
        reasons.append(
            f"저신뢰 신청자격 필드 {low_conf_field_count}건 "
            f"(>{_LOW_CONF_COUNT_THRESHOLD} 임계, <{_LOW_CONF_THRESHOLD} 신뢰도)"
        )
    if valid_tag_count == 0:
        reasons.append("유효 태그 0건 (태그 매칭 입력 부재)")

    return Stage3Decision(needs_review=bool(reasons), reasons=tuple(reasons))


__all__ = ["Stage3Decision", "evaluate_stage3"]
