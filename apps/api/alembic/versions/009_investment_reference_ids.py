"""Investment reference IDs: folio_number (MF/RD) and demat_id (stock)."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("folio_number", sa.Text(), nullable=True))
    op.add_column("accounts", sa.Column("demat_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "demat_id")
    op.drop_column("accounts", "folio_number")
