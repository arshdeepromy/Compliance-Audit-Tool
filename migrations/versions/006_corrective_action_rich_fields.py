"""Add rich gap-item fields to corrective_action table.

Revision ID: 006_corrective_action_rich_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "006_corrective_action_rich_fields"
down_revision = "005_branding_header_footer"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("corrective_action") as batch_op:
        batch_op.add_column(sa.Column("gap_item_id", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("title", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("action_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("form_or_doc", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("quantity", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("max_age", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("max_age_months", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("signed", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("signed_by", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("category", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("criteria_codes", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("corrective_action") as batch_op:
        batch_op.drop_column("criteria_codes")
        batch_op.drop_column("category")
        batch_op.drop_column("signed_by")
        batch_op.drop_column("signed")
        batch_op.drop_column("max_age_months")
        batch_op.drop_column("max_age")
        batch_op.drop_column("quantity")
        batch_op.drop_column("form_or_doc")
        batch_op.drop_column("action_text")
        batch_op.drop_column("title")
        batch_op.drop_column("gap_item_id")
