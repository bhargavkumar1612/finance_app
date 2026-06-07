"""Add loan_type to accounts; consolidate legacy loan account types."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("loan_type", sa.Text(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE accounts
            SET account_type = 'loan',
                loan_type = CASE account_type
                    WHEN 'home_loan' THEN 'home'
                    WHEN 'personal_loan' THEN 'personal'
                    WHEN 'other_loan' THEN 'other'
                    ELSE loan_type
                END
            WHERE account_type IN ('home_loan', 'personal_loan', 'other_loan')
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE accounts
            SET account_type = CASE loan_type
                    WHEN 'home' THEN 'home_loan'
                    WHEN 'personal' THEN 'personal_loan'
                    WHEN 'other' THEN 'other_loan'
                    ELSE 'other_loan'
                END
            WHERE account_type = 'loan'
            """
        )
    )
    op.drop_column("accounts", "loan_type")
