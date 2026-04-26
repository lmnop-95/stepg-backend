"""add FK / reverse-PK indexes + final_score CHECK.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-26 14:30:00.000000+00:00

CodeRabbit PR #2 인덱스 누락 4종 + ProjectPostingMatch.final_score 도메인 CHECK
일괄 추가:

- `ix_projects_company_id` — `projects.company_id` 일반 B-tree (Q7).
  partial unique `ix_projects_default_per_company` (`WHERE is_default IS TRUE`)
  하나뿐이라 "특정 company의 모든 project" 풀 스캔.
- `ix_project_fields_of_work_field_of_work_id` — 복합 PK 역방향 (Q8).
  M3/M6 매칭 단계 FoW→projects 역방향 join.
- `ix_attachments_posting_id` — FK 인덱스 (Q15). Postgres FK 자동 인덱스 X.
  CASCADE 삭제 성능 + posting별 첨부 조회.
- `ix_posting_fields_of_work_field_of_work_id` — 복합 PK 역방향 (Q16).
  M3/M6 FoW→postings 역방향 join.
- `ck_project_posting_matches_final_score_range` — `0 <= final_score <= 1`
  (Q10/Q12). MatchScore (§4.3) 0..1 정규화 last-line-of-defense.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_projects_company_id", "projects", ["company_id"])
    op.create_index(
        "ix_project_fields_of_work_field_of_work_id",
        "project_fields_of_work",
        ["field_of_work_id"],
    )
    op.create_index("ix_attachments_posting_id", "attachments", ["posting_id"])
    op.create_index(
        "ix_posting_fields_of_work_field_of_work_id",
        "posting_fields_of_work",
        ["field_of_work_id"],
    )
    op.create_check_constraint(
        op.f("ck_project_posting_matches_final_score_range"),
        "project_posting_matches",
        "final_score >= 0 AND final_score <= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_project_posting_matches_final_score_range"),
        "project_posting_matches",
        type_="check",
    )
    op.drop_index(
        "ix_posting_fields_of_work_field_of_work_id", table_name="posting_fields_of_work"
    )
    op.drop_index("ix_attachments_posting_id", table_name="attachments")
    op.drop_index(
        "ix_project_fields_of_work_field_of_work_id", table_name="project_fields_of_work"
    )
    op.drop_index("ix_projects_company_id", table_name="projects")
