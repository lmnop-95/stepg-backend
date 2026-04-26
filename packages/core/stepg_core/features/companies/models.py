from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from stepg_core.db.base import Base, TimestampMixin

CORPORATE_TYPES: tuple[str, ...] = ("법인", "개인사업자", "비영리법인", "기타")
"""§8.2 기업형태 4종. CHECK constraint 값. SoT는 이 상수 — `_CORPORATE_TYPE_CHECK_SQL`이
이 상수에서 SQL 표현을 생성하므로 ORM constraint와 마이그레이션이 자동 동기화."""

CERTIFICATIONS: tuple[str, ...] = (
    "벤처기업",
    "이노비즈",
    "메인비즈",
    "여성기업",
    "장애인기업",
    "소셜벤처",
)
"""`docs/ARCHITECTURE.md §8.2` SoT. M5 onboarding form + M9 admin form에서 import."""

_CORPORATE_TYPE_CHECK_SQL = f"corporate_type IN ({', '.join(repr(t) for t in CORPORATE_TYPES)})"


class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (CheckConstraint(_CORPORATE_TYPE_CHECK_SQL, name="corporate_type_allowed"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    biz_reg_no: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    corporate_type: Mapped[str] = mapped_column(String(16), nullable=False)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_last_year: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sido: Mapped[str] = mapped_column(String(16), nullable=False)
    certifications: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    industry_ksic_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
