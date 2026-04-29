"""CLOVA Document OCR bizLicense source — async client + raw → DTO mapping.

Recon: `docs/.local/feat/onboarding/M5-api/clova-ocr-recon.md` (gitignored).
Spec memory: `~/.claude-work/.../reference_clova_bizlicense_api.md`.

Legacy (`docs/legacy/pitfalls.md` §M5):
- L1: 30s `asyncio.timeout` budget around `fetch_with_retry`. CLOVA OCR
  averages 5~10s, p99 20s+; httpx default timeout (15s) is unsafe for OCR.
- L2: tenacity retry policy reused via `fetch_with_retry` (3 attempts =
  initial + 2 retries, matches "1~2회 재시도" guideline).
- L4: this module owns CLOVA-shape parsing; FE never sees raw response.
- L5: BE→CLOVA uses JSON+base64 (Q18). FE→BE multipart handling lives in the
  route layer (commit 3).
- L9: bizLicense template returns structured fields in a single call — no
  LLM second pass.
- D / Q26 (2026-04-29): single-page PDF allowed. Multi-page PDF is rejected
  by CLOVA (`code=0011`) and surfaces here as `ocr_pdf_multi_page`.

Public API (Q27): `recognize_bizlicense(image, mime_type) -> OcrBizRegResponse`,
`OcrCallError` (domain exception with snake_case `code`).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
import uuid
from datetime import date
from typing import Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from stepg_core.core.biz_reg_no import normalize_to_digits
from stepg_core.core.config import get_settings
from stepg_core.core.errors import HttpFetchError, OcrCallError
from stepg_core.core.http import DEFAULT_TIMEOUT_SECONDS, fetch_with_retry
from stepg_core.features.onboarding.schemas import (
    BizLicenseElementRaw,
    BizLicenseResponseRaw,
    BizLicenseResultRaw,
    OcrBizRegResponse,
)

logger = logging.getLogger(__name__)

_OCR_TIMEOUT_SECONDS: Final[float] = 30.0
_API_VERSION: Final[str] = "V2"
_REQUEST_IMAGE_NAME: Final[str] = "biz_license"

_KOREAN_DATE_RE = re.compile(r"^\s*(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*$")

# Q29 whitelist: jpg/jpeg/png/pdf only. tif/tiff excluded — Phase 1.5 lift.
# `image/jpg` (non-standard) is normalized to `image/jpeg` upstream by
# `upload_validator._MIME_NORMALIZE` (Q4 pass3 — single SoT in validator);
# this map only sees canonical MIMEs.
_FORMAT_MAP: Final[dict[str, str]] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
}

# Multi-page PDF rejection sentinel — recon (2026-04-29) saw `code=0011` with
# this exact message fragment. The CLOVA error response shape is
# `{code, message, path, traceId, timestamp}`.
_MULTI_PAGE_MSG_FRAGMENT: Final[str] = "Special models do not support multiple PDF or Tiff"

# Exception tuple kept as a Name binding — ruff format normalizes the inline
# `except (A, B):` form to PEP 758 paren-less `except A, B:` (Python 3.14+),
# which visually collides with the deprecated Python 2 `except A, B:` (=
# `except A as B:`) and triggers reviewer / CodeRabbit forensics. Capturing the
# tuple here keeps the call-site unambiguous.
_PARSE_EXCEPTIONS: Final[tuple[type[Exception], ...]] = (ValueError, ValidationError)


class _ClovaErrorBody(BaseModel):
    """Subset of CLOVA's HTTP-error response — we only inspect `message` here.

    Full shape: `{code, message, path, traceId, timestamp}`. `extra="ignore"`
    keeps the parse robust to vendor field changes.
    """

    model_config = ConfigDict(extra="ignore")
    code: str = ""
    message: str = ""


def _parse_korean_date(raw: str) -> date | None:
    """Parse 'YYYY 년 MM 월 DD 일' (CLOVA emits literal 한국어 + spaces)."""
    m = _KOREAN_DATE_RE.match(raw)
    if m is None:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _first_text(elements: tuple[BizLicenseElementRaw, ...]) -> str | None:
    for el in elements:
        if el.text:
            return el.text
    return None


def _all_texts(elements: tuple[BizLicenseElementRaw, ...]) -> tuple[str, ...]:
    return tuple(el.text for el in elements if el.text)


def _dedupe_preserve_order(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _map_to_dto(result: BizLicenseResultRaw) -> OcrBizRegResponse:
    biz_reg_raw = _first_text(result.registerNumber)
    open_date_raw = _first_text(result.openDate)
    issuance_date_raw = _first_text(result.issuanceDate)

    return OcrBizRegResponse(
        corp_name=_first_text(result.corpName),
        company_name=_first_text(result.companyName),
        representative_names=_all_texts(result.repName),
        biz_reg_no=normalize_to_digits(biz_reg_raw) if biz_reg_raw else None,
        corp_reg_no=_first_text(result.corpRegisterNum),
        business_address=_first_text(result.bisAddress),
        head_address=_first_text(result.headAddress),
        # bisType repeats per bisItem in multi-business 사업자등록증 — dedupe so
        # downstream KSIC mapping (commit 4) sees a unique set.
        business_types=_dedupe_preserve_order(_all_texts(result.bisType)),
        business_items=_all_texts(result.bisItem),
        business_area=_first_text(result.bisArea),
        established_on=_parse_korean_date(open_date_raw) if open_date_raw else None,
        issuance_date=_parse_korean_date(issuance_date_raw) if issuance_date_raw else None,
        tax_type=_first_text(result.taxType),
        document_type=_first_text(result.documentType),
    )


def _map_http_error(e: HttpFetchError) -> OcrCallError:
    """Translate transport-level `HttpFetchError` into domain `OcrCallError`.

    The cause's response body carries CLOVA's `code/message` for known cases
    (e.g. multi-page PDF). Body content is *not* logged here (legacy C4) —
    only the snake_case `code` and HTTP status surface in error pipelines.
    """
    if isinstance(e.cause, httpx.HTTPStatusError):
        try:
            body = _ClovaErrorBody.model_validate(e.cause.response.json())
        except _PARSE_EXCEPTIONS:
            body = None
        if body is not None and _MULTI_PAGE_MSG_FRAGMENT in body.message:
            return OcrCallError(
                code="ocr_pdf_multi_page", message=body.message, http_status=e.status
            )
    return OcrCallError(code="ocr_call_failed", message="", http_status=e.status)


async def recognize_bizlicense(image: bytes, mime_type: str) -> OcrBizRegResponse:
    """Call CLOVA bizLicense OCR and return the boundary DTO.

    `image` — raw bytes from the FE→BE multipart upload (route layer in
    commit 3 enforces size + magic-bytes validation).
    `mime_type` — the route-validated MIME, mapped here to CLOVA's
    `images[].format` value via `_FORMAT_MAP` (Q29).

    Raises `OcrCallError` for misconfiguration, timeout, transport errors,
    response shape changes, and CLOVA-side inference failures. Service layer
    (commit 5) maps these to FastAPI `HTTPException` (Q23).
    """
    fmt = _FORMAT_MAP.get(mime_type)
    if fmt is None:
        # Belt-and-suspenders — the route layer should have rejected this MIME
        # already (Q29 whitelist). Surfacing here keeps the source self-defending
        # if invoked from a future caller that skipped validation.
        raise OcrCallError(
            code="ocr_unsupported_media",
            message=f"unsupported MIME type: {mime_type!r}",
        )

    settings = get_settings()
    if settings.clova_ocr_bizlicense_invoke_url is None:
        raise OcrCallError(
            code="ocr_misconfigured",
            message="CLOVA_OCR_BIZLICENSE_INVOKE_URL 미설정",
        )
    if settings.clova_ocr_bizlicense_secret is None:
        raise OcrCallError(
            code="ocr_misconfigured",
            message="CLOVA_OCR_BIZLICENSE_SECRET 미설정",
        )

    body = {
        "version": _API_VERSION,
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "images": [
            {
                "format": fmt,
                "name": _REQUEST_IMAGE_NAME,
                "data": base64.b64encode(image).decode(),
            }
        ],
    }
    headers = {
        "X-OCR-SECRET": settings.clova_ocr_bizlicense_secret.get_secret_value(),
    }

    try:
        async with asyncio.timeout(_OCR_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                response = await fetch_with_retry(
                    client,
                    "POST",
                    settings.clova_ocr_bizlicense_invoke_url,
                    headers=headers,
                    json=body,
                )
                raw = response.json()
    except HttpFetchError as e:
        raise _map_http_error(e) from e
    except TimeoutError as e:
        raise OcrCallError(
            code="ocr_timeout",
            message=f"CLOVA OCR 호출 {_OCR_TIMEOUT_SECONDS}초 초과",
        ) from e

    try:
        parsed = BizLicenseResponseRaw.model_validate(raw)
    except ValidationError as e:
        # PII-safe logging: only error locations, never `input_value` (legacy C4
        # pitfalls — OCR raw response carries 사업자번호/대표자명/주소 등 PII).
        # `e.errors()` includes input_value; only `loc` is safe to surface.
        error_locs = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.warning(
            "CLOVA bizLicense 응답 shape 변경 — %d errors at %s",
            e.error_count(),
            error_locs,
        )
        raise OcrCallError(
            code="ocr_invalid_response_shape",
            message="CLOVA 응답 스키마가 기대 shape과 다릅니다",
        ) from e

    image_result = parsed.images[0]
    if image_result.inferResult != "SUCCESS":
        raise OcrCallError(
            code="ocr_inference_failed",
            message=image_result.message or image_result.inferResult,
        )
    if image_result.bizLicense is None:
        raise OcrCallError(
            code="ocr_invalid_response_shape",
            message="bizLicense 결과 누락",
        )

    return _map_to_dto(image_result.bizLicense.result)


__all__ = ["recognize_bizlicense"]
