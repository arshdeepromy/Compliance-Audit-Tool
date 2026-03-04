"""Add passkey table and dual MFA columns to user.

Revision ID: 002_passkey_dual_mfa
Revises: 001_initial
Create Date: 2026-03-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002_passkey_dual_mfa"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # New columns on user for dual MFA
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("mfa_totp_enabled", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("mfa_email_enabled", sa.Boolean(), nullable=False, server_default="0")
        )

    # Passkey / WebAuthn credentials table
    op.create_table(
        "user_passkey",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("credential_id", sa.Text(), unique=True, nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(100), nullable=False, server_default="My Passkey"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("user_passkey")
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("mfa_email_enabled")
        batch_op.drop_column("mfa_totp_enabled")
        batch_op.drop_column("email_verified")
