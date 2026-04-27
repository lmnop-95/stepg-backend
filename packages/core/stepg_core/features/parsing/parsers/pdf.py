"""PDF (.pdf) parser — `pdfplumber` 1차 + `easyocr` fallback (M3 commit 3).

페이지 단위로 `pdfplumber.Page.extract_text()` 1차 시도. 추출 글자수가 임계
(`Settings.pdf_ocr_fallback_min_chars_per_page`, default 50) 미만이면 그
페이지만 easyocr CPU mode 로 OCR fallback (텍스트+이미지 혼합 PDF 대응 — Q26).

`easyocr.Reader` 는 `lru_cache(maxsize=1)` 기반 lazy singleton (Q27). 첫 호출
시 모델 (수백 MB) 다운로드 — dev 첫 실행은 plan Q9 의 사전 cache cli 권장
(`uv run python -c 'import easyocr; easyocr.Reader(["ko","en"], gpu=False)'`).

per-page OCR timeout 120s — `concurrent.futures.ThreadPoolExecutor` +
`future.result(timeout)`. timeout / OCR 자체 raise (모델 OOM/decode/etc) 모두
그 페이지 skip + WARN log, 나머지 페이지 진행 (Q28). attachment 단위 fail 정책은
caller(commit 6 `parse_attachments`) broad except 로 시 계층화 (timeout 외
predicate-와 통일된 page-skip 정책).

PDF → image 변환은 `pdfplumber.Page.to_image(resolution=200).original` (PIL
Image) → `BytesIO` PNG 직렬화 후 easyocr 에 bytes 전달 (Q29). numpy 직접
의존 회피.
"""

from __future__ import annotations

import concurrent.futures
import io
import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Final, cast

import pdfplumber
from stepg_core.core.config import get_settings
from stepg_core.features.parsing.schemas import ParsedDocument

if TYPE_CHECKING:
    from pathlib import Path

    import easyocr
    from pdfplumber.page import Page

logger = logging.getLogger(__name__)

_OCR_PAGE_TIMEOUT_SECONDS: Final = 120.0
_OCR_RESOLUTION: Final = 200
_OCR_LANGUAGES: Final = ("ko", "en")


@lru_cache(maxsize=1)
def _get_reader() -> easyocr.Reader:
    import easyocr

    return easyocr.Reader(list(_OCR_LANGUAGES), gpu=False)


def _ocr_page_text(page: Page) -> str | None:
    image = page.to_image(resolution=_OCR_RESOLUTION).original
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    payload = buf.getvalue()
    reader = _get_reader()

    def _run_ocr() -> list[str]:
        # easyocr ships no type stubs — readtext returns `list[str]` when detail=0
        # but its static signature unions all variants.
        return cast(
            "list[str]",
            reader.readtext(payload, detail=0, paragraph=True),  # pyright: ignore[reportUnknownMemberType]
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_ocr)
        try:
            result = future.result(timeout=_OCR_PAGE_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            logger.warning(
                "pdf_ocr_page_timeout page=%d timeout=%.1fs",
                page.page_number,
                _OCR_PAGE_TIMEOUT_SECONDS,
            )
            return None
        except Exception as exc:
            # easyocr 의 다양한 raise(model OOM/decode error/CUDA glitch 등)
            # 를 page-skip 으로 demote — timeout 과 동일한 attachment 보존 정책 (Q3 critic Pass 4).
            logger.warning(
                "pdf_ocr_page_failed page=%d cause=%s: %s",
                page.page_number,
                type(exc).__name__,
                exc,
            )
            return None
    return "\n\n".join(result)


def parse(path: Path) -> ParsedDocument:
    threshold = get_settings().pdf_ocr_fallback_min_chars_per_page
    paragraphs: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text) < threshold:
                ocr_text = _ocr_page_text(page)
                if ocr_text is not None:
                    text = ocr_text
            for chunk in text.split("\n\n"):
                stripped = chunk.strip()
                if stripped:
                    paragraphs.append(stripped)

    return ParsedDocument(
        text="\n\n".join(paragraphs),
        paragraphs=paragraphs,
    )


__all__ = ["parse"]
