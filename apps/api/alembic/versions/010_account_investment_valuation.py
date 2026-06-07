"""Add invested_amount and current_value to accounts for holdings P&L."""
from alembic import op
import sqlalchemy as sa

revision = "010_account_investment_valuation"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("invested_amount", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("current_value", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "current_value")
    op.drop_column("accounts", "invested_amount")
