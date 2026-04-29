"""Onboarding ORM models.

Phase 1 holds a single reference table — `Ksic` (한국표준산업분류 11차) —
loaded once via `0014_ksic_codes.py` data migration and then read-only at
runtime. Q40 (minimal columns: code + name only); hierarchy / level /
deprecated_at / aliases stay deferred to Phase 1.5 when M6 매칭 누락률
측정으로 필요성이 확정될 때까지 보류.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from stepg_core.db.base import Base


class Ksic(Base):
    """한국표준산업분류 (KSIC 11차) 코드 ↔ 분류명 매핑.

    Q39 + Q44: 통계청 11차 (2024-07-01 시행). 5단계 코드 (1자/2자/3자/4자/5자
    각각 21 / 77 / 234 / 499 / 1196 = 2027 unique rows). M1 의
    `Company.industry_ksic_code String(5)` 와 동일 길이 제약.
    """

    __tablename__ = "ksic_codes"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


__all__ = ["Ksic"]
