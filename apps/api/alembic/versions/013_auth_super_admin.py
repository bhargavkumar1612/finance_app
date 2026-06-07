"""Auth + super admin (Round 9, ADR 003).

- Migrate users.email -> users.username (unique, not null)
- Add password_hash, role, status, rejected_at to users
- New tables: auth_tokens, password_reset_requests
- Existing rows are set status=approved / role=user so current data is not
  locked out; new registrations default to pending (app-level).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "013_auth_super_admin"
down_revision = "012_user_financial_persona"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. New user columns. role/status get server_defaults so existing rows
    #    backfill to approved/user (pre-deployment dev data stays usable).
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.Text(), nullable=False, server_default="user"),
    )
    op.add_column(
        "users",
        sa.Column("status", sa.Text(), nullable=False, server_default="approved"),
    )
    op.add_column("users", sa.Column("rejected_at", sa.DateTime(), nullable=True))

    # 2. Backfill any null email before it becomes a NOT NULL username.
    op.execute("UPDATE users SET email = 'legacy-' || id::text WHERE email IS NULL")

    # 2b. Give pre-existing (legacy email-only) users a known temporary password
    #     so they can sign in after the cutover. They should reset it via the
    #     forgot-password flow. New registrations set their own password.
    import bcrypt  # available in the api image where migrations run

    legacy_hash = bcrypt.hashpw(b"Password@123", bcrypt.gensalt()).decode("utf-8")
    op.execute(f"UPDATE users SET password_hash = '{legacy_hash}' WHERE password_hash IS NULL")

    # 3. Rename email -> username (unique index on the column is preserved).
    op.alter_column("users", "email", new_column_name="username")
    op.alter_column("users", "username", existing_type=sa.Text(), nullable=False)

    # 4. Future inserts default to pending; existing rows already approved above.
    op.alter_column("users", "status", server_default="pending")

    # 5. Session tokens (only the sha256 hash is stored).
    op.create_table(
        "auth_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])

    # 6. Forgot-password queue.
    op.create_table(
        "password_reset_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_password_reset_requests_user_id", "password_reset_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_requests_user_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")
    op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    op.alter_column("users", "username", new_column_name="email")
    op.alter_column("users", "email", existing_type=sa.Text(), nullable=True)
    op.drop_column("users", "rejected_at")
    op.drop_column("users", "status")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
