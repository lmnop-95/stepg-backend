from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from stepg_core.db.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "ix_projects_default_per_company",
            "company_id",
            unique=True,
            postgresql_where=text("is_default IS TRUE"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


project_fields_of_work = Table(
    "project_fields_of_work",
    Base.metadata,
    Column(
        "project_id",
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "field_of_work_id",
        PGUUID(as_uuid=True),
        ForeignKey("fields_of_work.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
"""Project ↔ FieldOfWork N:M (Phase 1 Top3 enforced at service layer)."""


__all__ = ["Project", "project_fields_of_work"]
