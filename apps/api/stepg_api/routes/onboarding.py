"""M5-api onboarding routes — OCR preview (commit 4) + complete (commit 5).

`POST /onboarding/ocr`: multipart upload → DoS-safe chunked read → magic-bytes /
size / single-page PDF validation → CLOVA bizLicense → boundary DTO. Result
is preview-only, not persisted (pitfalls D — user edits the result before
`POST /onboarding/complete` saves it as `Company`).

NextAuth JWT protection lands in commit 7 via `app.include_router(deps=...)`
(Q37 — dev-only exposure during commit 4~6).

Korean user-facing detail (CLAUDE.md absolute rule E + pitfalls C4): the
route owns the `code → 한국어 message` lookup table. `OcrCallError.message`
remains internal-only — never echoed to FE (Q2 pass3 contract).
"""

from __future__ import annotations

import logging
from typing import Final

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from stepg_core.core.errors import OcrCallError
from stepg_core.features.onboarding.schemas import OcrBizRegResponse
from stepg_core.features.onboarding.sources.clova_bizlicense import recognize_bizlicense
from stepg_core.features.onboarding.upload_validator import (
    MAX_UPLOAD_BYTES,
    validate_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Q1 pass3 — chunk size for the size-guarded read. 64 KB is the standard
# tradeoff (system call overhead vs spool-buffer footprint); httpx /
# stream_to_temp_with_retry use 8 KB but they hash + write to disk, so the
# event-loop cost matters more there. We just accumulate in RAM up to 10 MB.
_READ_CHUNK_BYTES: Final[int] = 64 * 1024

# Q36 — semantic HTTP status per `OcrCallError.code`. Default for unknown
# codes is 502 (treat as upstream/source-side failure).
_OCR_ERROR_STATUS: Final[dict[str, int]] = {
    "ocr_unsupported_media": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "ocr_payload_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "ocr_pdf_multi_page": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "ocr_inference_failed": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "ocr_misconfigured": status.HTTP_503_SERVICE_UNAVAILABLE,
    "ocr_timeout": status.HTTP_504_GATEWAY_TIMEOUT,
    "ocr_call_failed": status.HTTP_502_BAD_GATEWAY,
    "ocr_invalid_response_shape": status.HTTP_502_BAD_GATEWAY,
}

# Q2 pass3 — Korean user-facing detail per error code (CLAUDE.md rule E).
# Internal `OcrCallError.message` may carry English upstream wording (e.g.
# CLOVA `code=0011` "Special models do not support multiple PDF or Tiff.")
# or include byte counts / type names — never surface to FE.
_OCR_ERROR_KO: Final[dict[str, str]] = {
    "ocr_unsupported_media": "지원하지 않는 파일 형식입니다.",
    "ocr_payload_too_large": "파일 크기가 제한을 초과했습니다.",
    "ocr_pdf_multi_page": "단일 페이지 PDF만 업로드 가능합니다.",
    "ocr_inference_failed": "사업자등록증 인식에 실패했습니다. 사진을 다시 확인해주세요.",
    "ocr_misconfigured": "OCR 서비스 설정 오류입니다. 잠시 후 다시 시도해주세요.",
    "ocr_timeout": "OCR 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
    "ocr_call_failed": "OCR 호출에 실패했습니다. 잠시 후 다시 시도해주세요.",
    "ocr_invalid_response_shape": "OCR 응답 형식이 올바르지 않습니다.",
}

_OCR_FALLBACK_KO: Final[str] = "OCR 처리 중 오류가 발생했습니다."


def _to_http_exception(e: OcrCallError) -> HTTPException:
    return HTTPException(
        status_code=_OCR_ERROR_STATUS.get(e.code, status.HTTP_502_BAD_GATEWAY),
        detail={
            "code": e.code,
            "message": _OCR_ERROR_KO.get(e.code, _OCR_FALLBACK_KO),
        },
    )


async def _read_with_size_guard(upload: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in 64 KB chunks, aborting if the running total exceeds
    `max_bytes`.

    Cheap defense against `Content-Length` lies: an attacker streaming a 1 GB
    body forces FastAPI's `SpooledTemporaryFile` to spill to disk before
    `validate_upload` (which inspects the buffered bytes) ever sees the size.
    Aborting after the first over-budget chunk caps disk + memory pressure.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise OcrCallError(
                code="ocr_payload_too_large",
                message=f"upload exceeds {max_bytes}B during chunked read",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/ocr", response_model=OcrBizRegResponse)
async def post_ocr(file: UploadFile = File(...)) -> OcrBizRegResponse:
    """사업자등록증 OCR preview — DB 미저장.

    multipart upload → chunked size-guarded read → `validate_upload`
    (size + MIME + magic-bytes + 단일 페이지 PDF) → `recognize_bizlicense` →
    `OcrBizRegResponse`. multi-page PDF 는 BE 사전 검증으로 422 즉시 거부
    (CLOVA 호출 비용 절감, Q31).
    """
    try:
        content = await _read_with_size_guard(file, MAX_UPLOAD_BYTES)
        canonical_mime = validate_upload(content, file.content_type or "")
        return await recognize_bizlicense(content, canonical_mime)
    except OcrCallError as e:
        raise _to_http_exception(e) from e


__all__ = ["router"]
