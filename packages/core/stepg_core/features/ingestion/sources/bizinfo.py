"""bizinfo (`https://www.bizinfo.go.kr`) source adapter — fetch + normalize.

Returns `list[RawPostingPayload]`. Errors during a single item map are demoted
to `None` + warning so a malformed posting cannot poison the whole batch
(legacy B3).

API spec deviations baked in (`docs/legacy/pitfalls.md` §M2.A):
- Response envelope is `{"jsonArray": [...]}`, *not* the 공공데이터포털 standard
  `{"response": {"body": {"items": [...]}}}` (A1).
- Auth query param is `crtfcKey`, *not* `serviceKey` (A2).
- Endpoint is `/uss/rss/bizinfoApi.do`, *not* `bizPbancNewList.do` (A3).
- `reqstBeginEndDe` is a single string (`"YYYY-MM-DD ~ YYYY-MM-DD"`),
  *not* split begin/end fields (A4).
- Apply period values may be 한글 자유서술 (`"상시 접수"`, `"예산 소진시까지"`) — fail
  parse → `(None, None)` (A5/B2).
- 금액 필드 부재 across 100/100 sampled rows — `support_amount_krw` is always
  `None` for bizinfo (A6); body extraction is M4's job.
- `pblancUrl` may be a relative path; normalize via `urljoin` (B5).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time, timedelta, timezone
from typing import cast
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import ValidationError
from stepg_core.core.config import get_settings
from stepg_core.core.http import DEFAULT_TIMEOUT_SECONDS, fetch_with_retry
from stepg_core.features.ingestion.schemas import AttachmentRef, RawPostingPayload

logger = logging.getLogger(__name__)

_BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
_BIZINFO_BASE = "https://www.bizinfo.go.kr/"
_PAGE_SIZE = 100
_KST = timezone(timedelta(hours=9))
_DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d")
_KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        # surface mapping (RawPostingPayload fields, see plan §"bizinfo raw key → DTO 매핑")
        "pblancId",
        "pblancNm",
        "jrsdInsttNm",
        "excInsttNm",
        "pldirSportRealmLclasCodeNm",
        "reqstBeginEndDe",
        "pblancUrl",
        # attachments (Q81 — fileNm/flpthNm = original, printFileNm/printFlpthNm = PDF print)
        "fileNm",
        "flpthNm",
        "printFileNm",
        "printFlpthNm",
        # raw_payload-only (plan: "trgetNm/hashtags/reqstMthPapersCn/기타")
        "bsnsSumryCn",
        "trgetNm",
        "hashtags",
        "reqstMthPapersCn",
        # extra metadata observed in 2026-04-27 smoke call (raw_payload-only).
        # M2 시점 noise 제거용 — 이 키들의 *의미* 변경(예: `inqireCo` int→str)은
        # drift detector가 못 잡음. raw_payload diff 모니터링은 M3 이후 별도 구축.
        "creatPnttm",
        "updtPnttm",
        "inqireCo",
        "totCnt",
        "pldirSportRealmMlsfcCodeNm",
        "rceptEngnHmpgUrl",
        "refrncNm",
    }
)


def _opt_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _join_agencies(jrsd: object, exc: object) -> str | None:
    j = _opt_str(jrsd)
    e = _opt_str(exc)
    if j is not None and e is not None:
        return f"{j} / {e}"
    return j or e


def _parse_date(value: str, *, end_of_day: bool) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            d = datetime.strptime(value, fmt).date()  # noqa: DTZ007 — date-only intermediate
        except ValueError:
            continue
        local_time = time(23, 59, 59) if end_of_day else time(0, 0, 0)
        return datetime.combine(d, local_time, tzinfo=_KST).astimezone(UTC)
    return None


def _parse_date_range(value: object) -> tuple[datetime | None, datetime | None]:
    raw = _opt_str(value)
    if raw is None or "~" not in raw:
        return (None, None)
    begin_part, end_part = (s.strip() for s in raw.split("~", 1))
    begin = _parse_date(begin_part, end_of_day=False) if begin_part else None
    end = _parse_date(end_part, end_of_day=True) if end_part else None
    if begin is None or end is None:
        return (None, None)
    return (begin, end)


def _normalize_url(value: object) -> str | None:
    raw = _opt_str(value)
    if raw is None:
        return None
    if urlsplit(raw).scheme:
        return raw
    return urljoin(_BIZINFO_BASE, raw)


_ATTACHMENT_DELIMITER = "@"


def _split_attachment_field(value: object) -> list[str]:
    """bizinfo joins multi-attachment fields with `@` (e.g. `a.hwp@b.pdf@c.zip`).

    Single attachments arrive as bare strings without a delimiter, so the
    split handles both shapes uniformly. Empty / whitespace-only segments
    are dropped.

    Filenames containing `@` themselves are unsupported (Pass 8-O) — bizinfo
    has not been observed emitting such names; if a future drift produces
    misalignment, raw_payload comparison is the diagnostic path.
    """
    raw = _opt_str(value)
    if raw is None:
        return []
    return [s for s in (segment.strip() for segment in raw.split(_ATTACHMENT_DELIMITER)) if s]


def _extract_attachments(raw: dict[str, object]) -> tuple[AttachmentRef, ...]:
    """Pull `(fileNm, flpthNm)` + `(printFileNm, printFlpthNm)` pairs (Q81).

    Each pair may carry multiple attachments joined by `@` — original docs
    (`fileNm`/`flpthNm`, typically `.hwp`/`.zip`) and print-friendly PDFs
    (`printFileNm`/`printFlpthNm`). Names and URLs are split on the same
    delimiter and zipped pair-by-pair so a `_normalize_url` rejection drops
    *both* halves of that pair instead of shifting later URLs onto earlier
    filenames (Pass 8-J).
    """
    refs: list[AttachmentRef] = []
    for name_key, url_key in (("fileNm", "flpthNm"), ("printFileNm", "printFlpthNm")):
        names = _split_attachment_field(raw.get(name_key))
        url_segments = _split_attachment_field(raw.get(url_key))
        for filename, segment in zip(names, url_segments, strict=False):
            url = _normalize_url(segment)
            if url is None:
                logger.warning(
                    "bizinfo attachment URL 정규화 실패 — pair drop (filename=%s, segment=%r)",
                    filename,
                    segment,
                )
                continue
            refs.append(AttachmentRef(filename=filename, url=url))
    return tuple(refs)


def _extract_items(data: object) -> list[dict[str, object]]:
    if not isinstance(data, dict):
        raise RuntimeError(f"bizinfo 응답 타입 변경 — 기대 dict, 실제 {type(data).__name__}")
    typed_data = cast("dict[str, object]", data)
    if "jsonArray" not in typed_data:
        raise RuntimeError("bizinfo 응답 구조 변경 — `jsonArray` 키 부재")
    items_obj = typed_data["jsonArray"]
    if not isinstance(items_obj, list):
        raise RuntimeError(
            f"bizinfo `jsonArray` 타입 변경 — 기대 list, 실제 {type(items_obj).__name__}"
        )
    items_list = cast("list[object]", items_obj)
    return [item for item in items_list if isinstance(item, dict)]


def _detect_drift(items: list[dict[str, object]]) -> None:
    """Union all item keys — single warning per fetch with the full new-key set.

    Detecting on the first item only (legacy `seen_drift` flag) misses keys that
    appear in row N>0 — bizinfo carries optional fields that are absent in early
    rows. Union avoids that. Q62 + Q65: `_KNOWN_FIELDS` covers both surface
    mapping and raw_payload-only known keys.
    """
    if not items:
        return
    union_keys: set[str] = set()
    for item in items:
        union_keys.update(item.keys())
    drift = union_keys - _KNOWN_FIELDS
    if drift:
        logger.warning("bizinfo schema drift — 새 키 발견: %s", sorted(drift))


def _map_item(raw: dict[str, object]) -> RawPostingPayload | None:
    source_id = _opt_str(raw.get("pblancId"))
    title = _opt_str(raw.get("pblancNm"))
    if source_id is None or title is None:
        logger.warning(
            "bizinfo item skipped — 필수 키 누락 (pblancId=%r, pblancNm=%r)",
            raw.get("pblancId"),
            raw.get("pblancNm"),
        )
        return None
    apply_start, apply_end = _parse_date_range(raw.get("reqstBeginEndDe"))
    try:
        return RawPostingPayload(
            source="bizinfo",
            source_id=source_id,
            title=title,
            agency=_join_agencies(raw.get("jrsdInsttNm"), raw.get("excInsttNm")),
            category=_opt_str(raw.get("pldirSportRealmLclasCodeNm")),
            support_amount_krw=None,
            apply_start_at=apply_start,
            apply_end_at=apply_end,
            detail_url=_normalize_url(raw.get("pblancUrl")),
            attachments=_extract_attachments(raw),
            raw_payload=raw,
        )
    except ValidationError as e:
        # B3 정신: DTO validation 실패도 batch 폭사 금지 — 1건 skip + warn.
        # 미래 source 추가 시 timezone/length validator 변화에 대비한 안전망.
        logger.warning("bizinfo item skipped — DTO validation 실패 (pblancId=%r): %s", source_id, e)
        return None


async def fetch() -> list[RawPostingPayload]:
    settings = get_settings()
    if settings.bizinfo_api_key is None:
        raise RuntimeError("BIZINFO_API_KEY 미설정 — set env")
    params: dict[str, str | int] = {
        "crtfcKey": settings.bizinfo_api_key.get_secret_value(),
        "dataType": "json",
        "searchCnt": _PAGE_SIZE,
    }
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as client:
        response = await fetch_with_retry(client, "GET", _BIZINFO_URL, params=params)
    items = _extract_items(response.json())
    _detect_drift(items)
    payloads: list[RawPostingPayload] = [
        payload for item in items if (payload := _map_item(item)) is not None
    ]
    dropped = len(items) - len(payloads)
    logger.info(
        "bizinfo fetch: received=%d ingested=%d dropped=%d",
        len(items),
        len(payloads),
        dropped,
    )
    return payloads


__all__ = ["fetch"]
