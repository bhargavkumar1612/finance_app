"""Add nw_impact to transactions and parent_account_id to accounts

Revision ID: 005
Revises: 004
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("nw_impact", sa.Text(), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "accounts",
        sa.Column("parent_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "accounts_parent_account_id_fkey",
        "accounts",
        "accounts",
        ["parent_account_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("accounts_parent_account_id_fkey", "accounts", type_="foreignkey")
    op.drop_column("accounts", "parent_account_id")
    op.drop_column("transactions", "nw_impact")
