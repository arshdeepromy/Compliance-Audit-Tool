"""Add info_only flag to template_criterion and info_answer to audit_score.

Revision ID: 007_info_only_criteria
"""

from alembic import op
import sqlalchemy as sa

revision = "007_info_only_criteria"
down_revision = "006_corrective_action_rich_fields"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("template_criterion") as batch_op:
        batch_op.add_column(
            sa.Column("info_only", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )

    with op.batch_alter_table("audit_score") as batch_op:
        batch_op.add_column(sa.Column("info_answer", sa.Text(), nullable=True))

    # Backfill: mark MB50-MB54 as info_only in existing Tōtika template
    op.execute(
        sa.text(
            "UPDATE template_criterion SET info_only = 1 "
            "WHERE code IN ('MB50', 'MB51', 'MB52', 'MB53', 'MB54')"
        )
    )


def downgrade():
    with op.batch_alter_table("audit_score") as batch_op:
        batch_op.drop_column("info_answer")

    with op.batch_alter_table("template_criterion") as batch_op:
        batch_op.drop_column("info_only")
