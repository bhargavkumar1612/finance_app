"""Per-user financial persona for copilot personalization."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "012_user_financial_persona"
down_revision = "011_account_investment_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_financial_personas",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("traits", JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("user_financial_personas")
