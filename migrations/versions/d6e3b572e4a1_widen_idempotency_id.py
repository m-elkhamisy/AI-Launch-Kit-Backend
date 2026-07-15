"""widen idempotency record id

Revision ID: d6e3b572e4a1
Revises: b119f98f6b0e
Create Date: 2026-07-15 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e3b572e4a1"
down_revision: str | Sequence[str] | None = "b119f98f6b0e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.String(length=64),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
