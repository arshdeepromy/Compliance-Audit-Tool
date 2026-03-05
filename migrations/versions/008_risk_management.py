"""Enterprise Risk Management tables.

Revision ID: 008_risk_management
"""

from alembic import op
import sqlalchemy as sa

revision = "008_risk_management"
down_revision = "007_info_only_criteria"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "risk_category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "risk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("risk_category.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_source", sa.String(200), nullable=True),
        sa.Column("inherent_likelihood", sa.Integer(), nullable=True),
        sa.Column("inherent_impact", sa.Integer(), nullable=True),
        sa.Column("residual_likelihood", sa.Integer(), nullable=True),
        sa.Column("residual_impact", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Open"),
        sa.Column("treatment_type", sa.String(20), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("review_frequency_days", sa.Integer(), nullable=True, server_default="90"),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "risk_mitigation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risk.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("control_type", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Planned"),
        sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "risk_review",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risk.id"), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("review_date", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=True),
    )


def downgrade():
    op.drop_table("risk_review")
    op.drop_table("risk_mitigation")
    op.drop_table("risk")
    op.drop_table("risk_category")
