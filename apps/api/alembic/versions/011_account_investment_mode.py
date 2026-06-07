"""Add investment_mode to accounts for mutual fund one-time vs SIP."""
from alembic import op
import sqlalchemy as sa

revision = "011_account_investment_mode"
down_revision = "010_account_investment_valuation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("investment_mode", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "investment_mode")
