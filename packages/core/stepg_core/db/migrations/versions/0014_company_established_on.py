"""add Company.established_on DATE column.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-28 00:00:00.000000+00:00

M5-api commit 1 — M1 schema 누락 보강 (`docs/legacy/pitfalls.md` M5 D 함정).

CLOVA bizLicense OCR 응답에 사업자등록증 개업일이 포함되며, pitfalls D 는
이를 `TIMESTAMP WITH TIME ZONE` 이 아닌 **`DATE`** 로 저장하도록 명시:

> 개업일은 본질적으로 date-only. TIMESTAMPTZ 로 저장하면 FE 가 `Date` 객체로
> 읽으며 local timezone 으로 변환되어 "04월 01일 입력했는데 03월 31일로 표시됨"
> UX 사고가 발생.

M1 (`0003_users_companies_projects_fow.py`) 작성 시점에 누락된 컬럼이라 별도 PR
없이 M5-api PR 안에서 흡수. 다른 onboarding 컬럼(`industry_ksic_code` 등)은 이미
M1 에 박혀 있어 본 마이그레이션은 단일 컬럼만 다룸.

Column:
- `established_on DATE NULL`: 사업자등록증 개업일. CLOVA OCR confidence 가 낮거나
  사업자등록증 종류별로 비어 있는 경우가 있어 nullable. 강제 입력 정책은 M5
  commit 5 (`POST /onboarding/complete` 입력 검증) 에서 별도 결정.

Round-trip 테스트: `alembic upgrade head && downgrade -1 && upgrade head` 통과
(단순 `op.add_column` / `op.drop_column` 이라 추가 처리 없음).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("established_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "established_on")
