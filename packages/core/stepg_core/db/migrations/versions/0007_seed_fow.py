"""seed Fields of Work skeleton.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-26 13:00:00.000000+00:00

`docs/ARCHITECTURE.md §7.4` 초기 트리 골격 18 노드. UUID v4 리터럴로 영구 고정
(§7.1 "UUID로 영구 고정"). 노드 폐기는 soft delete (`deprecated_at`)이라
hard delete 비발생, 본 마이그레이션은 dev/prod 부팅 시 단일 적재.

aliases는 노드명 = alias 1개로 시작 (M4 Pre-work에서 5–15개로 확장).
industry_ksic_codes는 빈 배열 (M5 OCR 시점 / M4 Pre-work에서 매핑).
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (uuid, path, name) — §7.4 트리 골격 18 노드. 추가 시 UUID 새로 생성하여 append.
_NODES: list[tuple[str, str, str]] = [
    ("d6a29ff5-9109-48da-9081-9e7275419445", "tech", "기술개발"),
    ("2fb2ea23-a8d6-4491-af9f-1fd6f5d813cf", "tech.ai_ml", "AI/ML"),
    ("3710ae53-1851-472e-bf9c-4c9bea7ac99a", "tech.ai_ml.nlp", "자연어처리"),
    ("3ec41e1e-1dcd-402f-a66e-ad8f8caa6c8a", "tech.ai_ml.cv", "컴퓨터비전"),
    ("fe8074ab-4eb8-4e74-b1ba-4c5da1a72f6c", "tech.ai_ml.audio", "음성/오디오"),
    ("97e52027-71ea-460a-9fb4-09de22d36e83", "tech.bio", "바이오/헬스케어"),
    ("219a2fe9-97cb-4734-9553-9b8e9ff324f5", "tech.cleantech", "친환경/클린테크"),
    ("489ac5c9-9012-4b83-bcaa-057264c9e7e3", "tech.manufacturing", "제조/로봇/하드웨어"),
    ("4d5e2c88-477b-4b2a-8153-7f5b540745c3", "biz", "사업영역"),
    ("e8c4106c-0827-47d5-aa29-c6d250787c86", "biz.b2b_saas", "B2B SaaS"),
    ("82cfca8f-f571-435a-b30b-b55c59d2af6c", "biz.b2c_ecommerce", "B2C 이커머스"),
    ("676a8bae-726b-4de4-8729-13cb062bc427", "biz.content_media", "콘텐츠/미디어"),
    ("05e4ce4e-bcc1-4f21-8238-30c452d06d0b", "biz.fintech", "핀테크"),
    ("5fc5af99-5939-405d-a115-3226154beb4f", "biz.mobility", "모빌리티"),
    ("856c856e-b781-4566-ba01-2c8398c01d25", "stage", "사업 단계"),
    ("ace99e73-bce3-4a41-a71f-619114ed146f", "stage.early", "창업 초기 (3년 이내)"),
    ("4debd032-9d49-4016-a4d5-d866f0545244", "stage.growth", "성장기 (3-7년)"),
    ("f50355f5-45f7-4114-a213-72a0fe724acc", "stage.mature", "성숙기 (7년+)"),
]


_INSERT_SQL = sa.text(
    "INSERT INTO fields_of_work (id, name, path, aliases, industry_ksic_codes) "
    "VALUES (:id, :name, CAST(:path AS ltree), ARRAY[:alias]::text[], ARRAY[]::text[]) "
    "ON CONFLICT (id) DO NOTHING"
)

_DELETE_SQL = sa.text("DELETE FROM fields_of_work WHERE id IN :ids").bindparams(
    sa.bindparam("ids", expanding=True)
)


def upgrade() -> None:
    # raw SQL via sa.text bindparams: 마이그레이션이 ORM/feature 모듈 schema에 의존 안
    # 하도록 (Q89, alembic best practice). bindparams 자동 escape (Q92).
    # `UUID(...)` Python 객체로 전달해 asyncpg가 uuid 컬럼 타입 자동 인식.
    for node_id, path, name in _NODES:
        op.execute(
            _INSERT_SQL.bindparams(id=UUID(node_id), name=name, path=path, alias=name)
        )


def downgrade() -> None:
    # id (§7.1 영구 불변 UUID) 키로 매칭 (Q91). path는 후속 변경 가능.
    op.execute(_DELETE_SQL.bindparams(ids=[UUID(node_id) for node_id, _, _ in _NODES]))
