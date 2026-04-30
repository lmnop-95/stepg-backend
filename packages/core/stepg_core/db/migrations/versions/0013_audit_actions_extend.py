"""extend AUDIT_ACTIONS enum with STAGE2_INVALID_TAG / STAGE2_INVALID_FIELD.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-30 12:00:00.000000+00:00

M4 main commit 1 — `docs/PROMPTS.md §0` mandate. Stage 2 invalid 로깅
(`features/extraction/stage2.py`, M4 commit 5)이 본 enum 확장에 의존; 미반영 시
``IntegrityError: action_allowed CHECK constraint violation``.

CHECK constraint `ck_extraction_audit_logs_action_allowed` 갱신 패턴은 0008 mirror
(`op.drop_constraint` + `op.create_check_constraint`, ``type_="check"``). action 리스트는
raw SQL literal — alembic migration frozen-state 관행 (ORM `_AUDIT_ACTION_CHECK_SQL`이
런타임에 derived 되지만 마이그레이션은 박힌 시점 그대로).

downgrade: 기존 `STAGE2_INVALID_TAG` / `STAGE2_INVALID_FIELD` row가 있으면 Postgres CHECK
constraint creation 시 검사하므로 downgrade 실패. dev/CI round-trip test는 rows 없는
상태에서 통과. production rollback 시 운영자 수동 cleanup 가이드:

    DELETE FROM extraction_audit_logs
     WHERE action IN ('STAGE2_INVALID_TAG', 'STAGE2_INVALID_FIELD');

데이터 보존 invariant (`extraction_audit_logs` append-only,
`features/review/models.py::ExtractionAuditLog` docstring) 때문에 자동 DELETE는 박지 않음
— 운영자의 의식적 결정 후 수동 실행.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_extraction_audit_logs_action_allowed"),
        "extraction_audit_logs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_extraction_audit_logs_action_allowed"),
        "extraction_audit_logs",
        "action IN ('AUTO_APPROVE', 'MANUAL_APPROVE', 'EDIT', 'MANUAL_INSERT', 'REJECT', "
        "'STAGE2_INVALID_TAG', 'STAGE2_INVALID_FIELD')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_extraction_audit_logs_action_allowed"),
        "extraction_audit_logs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_extraction_audit_logs_action_allowed"),
        "extraction_audit_logs",
        "action IN ('AUTO_APPROVE', 'MANUAL_APPROVE', 'EDIT', 'MANUAL_INSERT', 'REJECT')",
    )
