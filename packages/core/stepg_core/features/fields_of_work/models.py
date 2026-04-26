from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime
from sqlalchemy_utils.primitives.ltree import Ltree
from sqlalchemy_utils.types.ltree import LtreeType
from stepg_core.db.base import Base


class FieldOfWork(Base):
    """Taxonomy node. UUID id is permanent (§7.1). Use deprecated_at for soft delete.

    `path` is annotated `Mapped[Ltree]`: `LtreeType` deserializes to a
    `sqlalchemy_utils.primitives.ltree.Ltree` object on read (exposes `.descendant_of()`
    etc. for M3 ltree queries). Write site accepts plain `str` via `Ltree(str)` cast.
    """

    __tablename__ = "fields_of_work"
    __table_args__ = (
        Index("ix_fields_of_work_path_gist", "path", postgresql_using="gist"),
        Index("ix_fields_of_work_aliases_gin", "aliases", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[Ltree] = mapped_column(LtreeType, nullable=False, unique=True)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    industry_ksic_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["FieldOfWork"]
