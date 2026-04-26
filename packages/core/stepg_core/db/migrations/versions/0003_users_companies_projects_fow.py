"""add User, Company, Project, FieldOfWork tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26 10:16:47.939001+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fields_of_work",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("path", sqlalchemy_utils.types.ltree.LtreeType(), nullable=False),
        sa.Column(
            "aliases",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "industry_ksic_codes",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fields_of_work")),
        sa.UniqueConstraint("path", name=op.f("uq_fields_of_work_path")),
    )
    op.create_index(
        "ix_fields_of_work_path_gist",
        "fields_of_work",
        ["path"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_fields_of_work_aliases_gin",
        "fields_of_work",
        ["aliases"],
        postgresql_using="gin",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("biz_reg_no", sa.String(length=10), nullable=False),
        sa.Column("corporate_type", sa.String(length=16), nullable=False),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("revenue_last_year", sa.BigInteger(), nullable=True),
        sa.Column("sido", sa.String(length=16), nullable=False),
        sa.Column(
            "certifications",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("industry_ksic_code", sa.String(length=5), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "corporate_type IN ('법인', '개인사업자', '비영리법인', '기타')",
            name=op.f("ck_companies_corporate_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_companies_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("biz_reg_no", name=op.f("uq_companies_biz_reg_no")),
        sa.UniqueConstraint("user_id", name=op.f("uq_companies_user_id")),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_projects_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index(
        "ix_projects_default_per_company",
        "projects",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )

    op.create_table(
        "project_fields_of_work",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("field_of_work_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["field_of_work_id"],
            ["fields_of_work.id"],
            name=op.f("fk_project_fields_of_work_field_of_work_id_fields_of_work"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_fields_of_work_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "field_of_work_id", name=op.f("pk_project_fields_of_work")
        ),
    )


def downgrade() -> None:
    op.drop_table("project_fields_of_work")
    op.drop_index(
        "ix_projects_default_per_company",
        table_name="projects",
        postgresql_where=sa.text("is_default IS TRUE"),
    )
    op.drop_table("projects")
    op.drop_table("companies")
    op.drop_table("users")
    op.drop_index("ix_fields_of_work_aliases_gin", table_name="fields_of_work")
    op.drop_index("ix_fields_of_work_path_gist", table_name="fields_of_work")
    op.drop_table("fields_of_work")
