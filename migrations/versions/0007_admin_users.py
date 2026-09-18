"""Platform admin user accounts and session management (admin console)."""

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA sahulat_admin")
    op.execute("REVOKE ALL ON SCHEMA sahulat_admin FROM PUBLIC")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(256), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="operator",
        ),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('admin', 'operator')", name="admin_user_role_valid"
        ),
        sa.CheckConstraint(
            "length(email) > 0",
            name="admin_user_email_not_empty",
        ),
        schema="sahulat_admin",
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema="sahulat_admin",
    )
    op.create_foreign_key(
        "sessions_user_id_fkey",
        source_table="sessions",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        source_schema="sahulat_admin",
        referent_schema="sahulat_admin",
    )
    op.create_index(
        "sessions_user_id_idx", "sessions", ["user_id"], schema="sahulat_admin"
    )
    op.create_index(
        "sessions_expires_idx", "sessions", ["expires_at"], schema="sahulat_admin"
    )
    op.execute("GRANT USAGE ON SCHEMA sahulat_admin TO sahulat_runtime")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON sahulat_admin.users TO sahulat_runtime"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        "sahulat_admin.sessions TO sahulat_runtime"
    )


def downgrade() -> None:
    op.execute("DROP TABLE sahulat_admin.sessions")
    op.execute("DROP TABLE sahulat_admin.users")
    op.execute("DROP SCHEMA sahulat_admin")
