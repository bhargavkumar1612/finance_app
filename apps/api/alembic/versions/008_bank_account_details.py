"""Optional bank account details: account number, IFSC, branch, notes."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("account_number", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("ifsc_code", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("branch", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("account_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "account_notes")
    op.drop_column("accounts", "branch")
    op.drop_column("accounts", "ifsc_code")
    op.drop_column("accounts", "account_number")
