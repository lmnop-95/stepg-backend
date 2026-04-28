"""Attachment parsing orchestrator (M3 commit 1 SoT + commit 6 wire).

Routes downloaded attachments to format-specific parsers by filename
suffix (lowercase, derived inside this function from the supplied
filename — caller need not normalize). MIME은 dispatch에 사용 안 함
(`mimetypes.guess_type`이 `.hwpx`를 `application/octet-stream`으로 인식
하므로 — Q7).

`parse_attachment` is pure function (parser + splitter). `parse_attachments`
는 ARQ pipeline 통합 — `Attachment` row fetch + parse + status 마킹 + commit.

Exceptions as contract (Q6/Q7):
- `UnsupportedAttachmentFormatError`: suffix가 dispatch matrix에 없음
  → `parse_status='skipped_unsupported'`.
- 그 외 parser raise: caught → `parse_status='failed' +
  parse_error=f'{type(exc).__name__}: {exc}'` (Q71).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

import sqlalchemy as sa
from stepg_core.core.errors import UnsupportedAttachmentFormatError
from stepg_core.features.parsing.parsers import docx as docx_parser
from stepg_core.features.parsing.parsers import hwpx as hwpx_parser
from stepg_core.features.parsing.parsers import pdf as pdf_parser
from stepg_core.features.parsing.schemas import ParsedDocument
from stepg_core.features.parsing.sections import split_sections
from stepg_core.features.postings.models import Attachment, Posting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_ParserFn = Callable[[Path], ParsedDocument]

_DISPATCH: Final[dict[str, _ParserFn]] = {
    ".pdf": pdf_parser.parse,
    ".hwpx": hwpx_parser.parse,
    ".docx": docx_parser.parse,
}


@dataclass(frozen=True)
class ParseResult:
    """parse_attachments 카운터 (Q77).

    `parsed` 신규 ok / `skipped_unsupported` 미지원 포맷 (terminal) /
    `failed` parser raise (transient, retry 대상) / `skipped_idempotent`
    이미 ok·skipped_unsupported 라 SELECT 단계에서 제외 — daily cron 로그
    가시성용 (M9 admin queue 모니터링).
    """

    parsed: int
    skipped_unsupported: int
    failed: int
    skipped_idempotent: int


def _strip_nulls(s: str) -> str:
    # Postgres TEXT 컬럼은 NUL byte (0x00) 거부 (`CharacterNotInRepertoireError`).
    # 일부 PDF/HWPX 추출 결과에 binary glitch 형태로 섞여 들어옴 — boundary 한
    # 곳에서 정제해 모든 parser가 "DB-safe text" 계약 준수.
    return s.replace("\x00", "")


def parse_attachment(filename: str, path: Path) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    parser = _DISPATCH.get(suffix)
    if parser is None:
        raise UnsupportedAttachmentFormatError(suffix=suffix, filename=filename)

    document = parser(path)
    paragraphs = [_strip_nulls(p) for p in document.paragraphs]
    sections = {k: _strip_nulls(v) for k, v in split_sections(paragraphs).items()}
    return ParsedDocument(
        text=_strip_nulls(document.text),
        paragraphs=paragraphs,
        sections=sections,
    )


async def parse_attachments(session: AsyncSession, posting_ids: list[int]) -> ParseResult:
    """Parse Attachment rows for the given posting_ids (Q66).

    Idempotency at DB-level (Q67/Q69): SELECT WHERE `parse_status IN
    ('pending', 'failed')` — `ok` / `skipped_unsupported` 는 terminal 이라
    skip. `failed` 는 transient (network/lib bug fix 후 재시도 가치) 라
    매 cron 재시도 (Q70: 24h cooling 자연 발생).

    Per-attachment failures (Q73) — `UnsupportedAttachmentFormatError` →
    `parse_status='skipped_unsupported'` (terminal), 그 외 `Exception` →
    `parse_status='failed' + parse_error=f'{type}: {exc}'` (Q71). 모든 row
    update 후 single transaction at end commit (Q72, M2 패턴).

    Q10 (Batch A): posting의 모든 attachment가 parse 실패(extracted_text 모두
    NULL/empty)이면 `Posting.needs_review=true` 마킹 — M9 admin queue 진입
    통로. 일부만 실패는 안 건드림.
    """
    if not posting_ids:
        return ParseResult(parsed=0, skipped_unsupported=0, failed=0, skipped_idempotent=0)

    # idempotency 카운트용 — posting_ids 내 전체 attachment 수 (M9 운영 가시성, Q77).
    total_count = (
        await session.execute(
            sa.select(sa.func.count())
            .select_from(Attachment)
            .where(Attachment.posting_id.in_(posting_ids))
        )
    ).scalar_one()

    rows = await session.execute(
        sa.select(Attachment).where(
            Attachment.posting_id.in_(posting_ids),
            Attachment.parse_status.in_(("pending", "failed")),
        )
    )
    attachments = rows.scalars().all()

    parsed = 0
    skipped_unsupported = 0
    failed = 0
    for attachment in attachments:
        try:
            document = parse_attachment(attachment.filename, Path(attachment.local_path))
        except UnsupportedAttachmentFormatError:
            attachment.parse_status = "skipped_unsupported"
            attachment.extracted_text = None
            attachment.sections = None
            attachment.parse_error = None
            skipped_unsupported += 1
            logger.warning(
                "attachment 미지원 포맷 — id=%d filename=%s",
                attachment.id,
                attachment.filename,
            )
        except Exception as exc:  # noqa: BLE001 — Q73 broad catch by design
            attachment.parse_status = "failed"
            attachment.extracted_text = None
            attachment.sections = None
            attachment.parse_error = f"{type(exc).__name__}: {exc}"
            failed += 1
            logger.exception(
                "attachment parse 실패 — id=%d filename=%s",
                attachment.id,
                attachment.filename,
            )
        else:
            attachment.parse_status = "ok"
            attachment.extracted_text = document.text
            attachment.sections = document.sections
            attachment.parse_error = None
            parsed += 1
            logger.info(
                "attachment parsed — id=%d filename=%s text_chars=%d section_keys=%d",
                attachment.id,
                attachment.filename,
                len(document.text),
                len(document.sections),
            )

    # Q10: 모든 attachment 가 extracted_text NULL/empty 인 posting → needs_review=true.
    # `bool_and(...)` 가 True 인 posting 만 (한 row 라도 본문 있으면 False → 안 건드림).
    no_text_postings = (
        sa.select(Attachment.posting_id)
        .where(Attachment.posting_id.in_(posting_ids))
        .group_by(Attachment.posting_id)
        .having(
            sa.func.bool_and(
                sa.or_(Attachment.extracted_text.is_(None), Attachment.extracted_text == "")
            )
        )
    )
    await session.execute(
        sa.update(Posting).where(Posting.id.in_(no_text_postings)).values(needs_review=True)
    )

    await session.commit()
    skipped_idempotent = total_count - len(attachments)
    return ParseResult(
        parsed=parsed,
        skipped_unsupported=skipped_unsupported,
        failed=failed,
        skipped_idempotent=skipped_idempotent,
    )


__all__ = ["ParseResult", "parse_attachment", "parse_attachments"]
