"""Add header/footer branding columns to branding_settings.

Revision ID: 005
"""

from alembic import op
import sqlalchemy as sa

revision = "005_branding_header_footer"
down_revision = "004_action_tracking"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("branding_settings") as batch_op:
        batch_op.add_column(
            sa.Column("header_bg_colour", sa.String(7), nullable=False, server_default="#0a0a23")
        )
        batch_op.add_column(
            sa.Column("header_text_colour", sa.String(7), nullable=False, server_default="#ffffff")
        )
        batch_op.add_column(
            sa.Column("footer_text", sa.String(500), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("footer_bg_colour", sa.String(7), nullable=False, server_default="#0a0a23")
        )
        batch_op.add_column(
            sa.Column("footer_text_colour", sa.String(7), nullable=False, server_default="#94a3b8")
        )


def downgrade():
    with op.batch_alter_table("branding_settings") as batch_op:
        batch_op.drop_column("footer_text_colour")
        batch_op.drop_column("footer_bg_colour")
        batch_op.drop_column("footer_text")
        batch_op.drop_column("header_text_colour")
        batch_op.drop_column("header_bg_colour")
