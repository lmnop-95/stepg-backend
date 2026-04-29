"""Upload validation for the M5 onboarding OCR endpoint.

Layered validation (Q34 — feature-scoped helper between route and source):
- Q32: 10 MB size cap
- Q29: MIME whitelist (`image/jpeg`, `image/png`, `application/pdf`)
- Q7: manual magic-bytes signature check (JPEG/PNG/PDF only — pure Python,
  no `libmagic` system dep). Defeats polyglot uploads where the claimed MIME
  contradicts the actual byte signature.
- Q31: pypdf single-page enforcement (multi-page PDF → 422 `ocr_pdf_multi_page`
  before paying the CLOVA call cost — recon: CLOVA itself returns
  `code=0011` on multi-page, but BE rejection is faster + cheaper).

Raises `OcrCallError` (Q23 domain exception); the route layer maps the
`code` to an HTTP status (Q36 — semantic mapping table in
`apps/api/stepg_api/routes/onboarding.py`).
"""

from __future__ import annotations

import io
from typing import Final

import pypdf
from pypdf.errors import PdfReadError
from stepg_core.core.errors import OcrCallError

# Q32. Public so the route layer (commit 4) can apply the same cap as a
# pre-read DoS guard via chunked accumulator (Q1 pass3) — single SoT.
MAX_UPLOAD_BYTES: Final[int] = 10 * 1024 * 1024

# Q29 whitelist (canonical MIMEs only — `image/jpg` non-standard mapped below).
_ALLOWED_MIMES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png", "application/pdf"})

# Non-standard claimed MIMEs we tolerate by normalizing to the canonical form
# *before* the whitelist + magic-bytes cross-check. `image/jpg` is observed in
# the wild from older browsers / SDKs; the bytes are still JFIF/EXIF JPEG.
_MIME_NORMALIZE: Final[dict[str, str]] = {
    "image/jpg": "image/jpeg",
}

# Manual byte signatures (pure Python, no libmagic dep). Keys are MIME types,
# values are tuples of accepted leading-byte sequences. The PDF spec allows up
# to ~1024 bytes of header before `%PDF-`; we still require it at offset 0
# because Q31 + Q29 reject hybrid containers anyway.
_MIME_SIGNATURES: Final[dict[str, tuple[bytes, ...]]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
}


def _normalize(mime: str) -> str:
    return _MIME_NORMALIZE.get(mime, mime)


def _signature_matches(content: bytes, mime: str) -> bool:
    sigs = _MIME_SIGNATURES.get(mime)
    if sigs is None:
        return False
    return any(content.startswith(sig) for sig in sigs)


def validate_upload(content: bytes, claimed_mime: str) -> str:
    """Validate size, MIME whitelist, magic-bytes parity, and PDF single-page.

    Returns the canonical MIME (`image/jpeg` / `image/png` / `application/pdf`)
    for downstream consumption by `recognize_bizlicense`. Raises `OcrCallError`
    on any violation.
    """
    if len(content) > MAX_UPLOAD_BYTES:
        raise OcrCallError(
            code="ocr_payload_too_large",
            message=f"파일 크기 {len(content)}바이트 — 제한 {MAX_UPLOAD_BYTES}바이트 초과",
        )

    claimed = _normalize(claimed_mime)
    if claimed not in _ALLOWED_MIMES:
        raise OcrCallError(
            code="ocr_unsupported_media",
            message=f"지원하지 않는 미디어 형식: {claimed_mime!r}",
        )

    if not _signature_matches(content, claimed):
        raise OcrCallError(
            code="ocr_unsupported_media",
            message=f"파일 시그니처 불일치 (declared={claimed_mime!r})",
        )

    if claimed == "application/pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
        except (PdfReadError, ValueError) as e:
            raise OcrCallError(
                code="ocr_unsupported_media",
                message=f"PDF 파싱 실패 ({type(e).__name__})",
            ) from e
        if page_count > 1:
            raise OcrCallError(
                code="ocr_pdf_multi_page",
                message=f"단일 페이지 PDF만 허용 (입력 {page_count}페이지)",
            )

    return claimed


__all__ = ["MAX_UPLOAD_BYTES", "validate_upload"]
