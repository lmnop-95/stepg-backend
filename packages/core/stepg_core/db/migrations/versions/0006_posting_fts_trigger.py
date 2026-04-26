"""add tsvector trigger on posting for FTS.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-26 12:50:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION posting_search_vector_update()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    -- COALESCE는 현재 4 cols 모두 NOT NULL이라 dead code이지만 Phase 1.5+ ALTER로
    -- nullable 또는 server_default가 떼였을 때 트리거가 NULL || ' ' 평가로 NULL을
    -- 만들어 search_vector 깨지는 것을 막는 defense-in-depth.
    NEW.search_vector := to_tsvector(
        'simple',
        unaccent(
            coalesce(NEW.title, '') || ' '
            || coalesce(NEW.summary, '') || ' '
            || coalesce(NEW.target_description, '') || ' '
            || coalesce(NEW.support_description, '')
        )
    );
    RETURN NEW;
END;
$$
"""

_TRIGGER_SQL = """
CREATE TRIGGER posting_search_vector_trigger
BEFORE INSERT OR UPDATE OF title, summary, target_description, support_description
ON postings
FOR EACH ROW
EXECUTE FUNCTION posting_search_vector_update()
"""


def upgrade() -> None:
    # 기존 row backfill 안 함 (Phase 1 fresh DB 가정 — backend.md PR 순서가 마이그레이션
    # 순차 적용 + dev DB 정기 reset). Phase 1.5+ row 있는 DB에 도입 시 별도 backfill
    # 마이그레이션 필요 (예: `UPDATE postings SET title = title;`로 트리거 강제 발동).
    op.execute(_FUNCTION_SQL)
    op.execute(_TRIGGER_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS posting_search_vector_trigger ON postings")
    op.execute("DROP FUNCTION IF EXISTS posting_search_vector_update()")
