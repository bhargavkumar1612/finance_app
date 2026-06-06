"""Add credit_limit and currency to accounts

Revision ID: 004
Revises: 003
Create Date: 2026-05-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("credit_limit", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("currency", sa.Text(), nullable=False, server_default="INR"),
    )


def downgrade() -> None:
    op.drop_column("accounts", "currency")
    op.drop_column("accounts", "credit_limit")
