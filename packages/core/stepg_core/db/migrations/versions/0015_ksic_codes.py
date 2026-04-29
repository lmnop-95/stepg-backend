"""create ksic_codes table + seed KSIC 11차 (2027 rows).

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-29 00:00:00.000000+00:00

M5-api commit 6 — Q5/Q44 (옵션 A + 11차) plan 결정. 통계청 KSIC 11차
(2024-07-01 시행) 5단계 코드를 정적 reference table 로 적재. M5 commit 7
(`POST /onboarding/complete`) 가 OCR `bisType` (한국어 분류명) → KSIC 코드
변환에 사용 (`features/onboarding/ksic.py::lookup_ksic_code_by_name`).

CSV source: `packages/core/stepg_core/features/onboarding/data/ksic_11th.csv`
— 사용자가 통계청 KSSC 검색결과를 paste 한 raw text 를 worker 측 정리 script
로 변환 (`docs/.local/feat/onboarding/ksic_raw.txt` → 정규식으로 `<code>.<name>`
파싱 + 대분류 끝 `(NN~MM)` range suffix strip + whitespace 정규화 → `code,name`
CSV).

Level distribution (sanity 체크용):
  대분류 (1자, A~U):   21
  중분류 (2자):        77
  소분류 (3자):       234
  세분류 (4자):       499
  세세분류 (5자):    1196
  ----
  합계:             2027 unique rows

`code` PRIMARY KEY 가 uniqueness 강제 — CSV 가 duplicate 코드 포함 시
IntegrityError 로 loud-fail (의도된 fail-fast). Alembic semantic 상 `upgrade`
는 한 번만 실행되므로 idempotency 는 무관. downgrade 는 table drop.

`name` 은 insert 시점에 internal whitespace canonical 화 (`" ".join(split())`)
하여 DB 가 정규화된 form 만 보존 — runtime lookup (`features/onboarding/ksic.py`)
은 input 만 동일 정규화 후 `LOWER(name) == ?` 비교로 충분 (Q1 pass4 — 정규화
SoT 1곳).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _csv_path() -> Path:
    """Resolve the seed CSV via `stepg_core.__file__` so the path stays valid
    under both editable installs (parents[N] from the migration file) and
    site-packages installs.
    """
    import stepg_core

    pkg_root = Path(stepg_core.__file__).resolve().parent
    return pkg_root / "features/onboarding/data/ksic_11th.csv"


def _load_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with _csv_path().open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["code"].strip()
            # Q1 pass4 — DB stores canonical whitespace form (single internal
            # space, no edge whitespace). Runtime lookup applies the same
            # `" ".join(split())` to input → exact equality after `LOWER()`.
            name = " ".join(row["name"].split())
            if not code or not name:
                continue
            rows.append({"code": code, "name": name})
    return rows


def upgrade() -> None:
    op.create_table(
        "ksic_codes",
        sa.Column("code", sa.String(length=5), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
    )

    table = sa.table(
        "ksic_codes",
        sa.column("code", sa.String(length=5)),
        sa.column("name", sa.String(length=255)),
    )
    op.bulk_insert(table, _load_rows())


def downgrade() -> None:
    op.drop_table("ksic_codes")
