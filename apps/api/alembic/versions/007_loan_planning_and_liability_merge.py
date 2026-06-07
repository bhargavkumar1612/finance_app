"""Loan planning fields, sanctioned_amount, migrate liabilities to loan accounts."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LIABILITY_TYPE_TO_LOAN_TYPE = {
    "home_loan": "home",
    "personal_loan": "personal",
    "cc": "other",
    "other": "other",
}


def upgrade() -> None:
    op.add_column("accounts", sa.Column("sanctioned_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("accounts", sa.Column("interest_rate", sa.Numeric(5, 2), nullable=True))
    op.add_column("accounts", sa.Column("emi_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("accounts", sa.Column("tenure_months", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("accounts", sa.Column("due_day", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("loan_type_description", sa.Text(), nullable=True))

    conn = op.get_bind()

    # Move loan credit_limit -> sanctioned_amount
    conn.execute(
        sa.text(
            """
            UPDATE accounts
            SET sanctioned_amount = credit_limit,
                credit_limit = NULL
            WHERE account_type = 'loan' AND credit_limit IS NOT NULL
            """
        )
    )

    # Migrate liabilities -> loan accounts (attach to user's first bank/cash account)
    liabilities = conn.execute(
        sa.text(
            """
            SELECT l.id, l.user_id, l.liability_type, l.name, l.outstanding_amount,
                   l.interest_rate, l.emi, l.due_day
            FROM liabilities l
            """
        )
    ).fetchall()

    for row in liabilities:
        lid, user_id, liability_type, name, outstanding, interest_rate, emi, due_day = row
        parent = conn.execute(
            sa.text(
                """
                SELECT id FROM accounts
                WHERE user_id = :user_id AND account_type IN ('bank', 'cash')
                ORDER BY created_at ASC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).fetchone()
        if not parent:
            continue

        loan_type = LIABILITY_TYPE_TO_LOAN_TYPE.get(liability_type, "other")
        loan_type_desc = "Migrated from liabilities" if loan_type == "other" else None

        account_id = conn.execute(
            sa.text(
                """
                INSERT INTO accounts (
                    id, user_id, account_type, name, institution, loan_type,
                    loan_type_description, sanctioned_amount, interest_rate, emi_amount,
                    due_day, currency, parent_account_id, created_at
                )
                VALUES (
                    gen_random_uuid(), :user_id, 'loan', :name, NULL, :loan_type,
                    :loan_type_desc, :outstanding, :interest_rate, :emi,
                    :due_day, 'INR', :parent_id, NOW()
                )
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "name": name,
                "loan_type": loan_type,
                "loan_type_desc": loan_type_desc,
                "outstanding": outstanding,
                "interest_rate": interest_rate,
                "emi": emi,
                "due_day": due_day,
                "parent_id": parent[0],
            },
        ).scalar()

        if outstanding and float(outstanding) > 0:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO transactions (
                        id, user_id, account_id, amount, currency, transaction_date,
                        merchant, category, source, nw_impact, created_at
                    )
                    VALUES (
                        gen_random_uuid(), :user_id, :account_id, :amount, 'INR',
                        CURRENT_DATE, :merchant, 'emi', 'manual', 'spending', NOW()
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "account_id": account_id,
                    "amount": -abs(float(outstanding)),
                    "merchant": f"Opening balance — {name}",
                },
            )

    conn.execute(
        sa.text(
            """
            UPDATE accounts AS l
            SET parent_account_id = sub.id
            FROM (
                SELECT DISTINCT ON (user_id) user_id, id
                FROM accounts
                WHERE account_type IN ('bank', 'cash')
                ORDER BY user_id, created_at ASC
            ) AS sub
            WHERE l.account_type = 'loan'
              AND l.parent_account_id IS NULL
              AND l.user_id = sub.user_id
            """
        )
    )

    conn.execute(sa.text("DELETE FROM liabilities"))
    op.drop_table("liabilities")


def downgrade() -> None:
    op.create_table(
        "liabilities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("liability_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("outstanding_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("emi", sa.Numeric(14, 2), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE accounts
            SET credit_limit = sanctioned_amount,
                sanctioned_amount = NULL
            WHERE account_type = 'loan' AND sanctioned_amount IS NOT NULL
            """
        )
    )

    op.drop_column("accounts", "loan_type_description")
    op.drop_column("accounts", "due_day")
    op.drop_column("accounts", "start_date")
    op.drop_column("accounts", "tenure_months")
    op.drop_column("accounts", "emi_amount")
    op.drop_column("accounts", "interest_rate")
    op.drop_column("accounts", "sanctioned_amount")
