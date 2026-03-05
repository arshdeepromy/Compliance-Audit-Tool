"""Add notes, resolution_notes to corrective_action and create action_evidence table.

Revision ID: 004_action_tracking
Revises: 003_compliance_framework
"""

import sqlalchemy as sa
from alembic import op

revision = "004_action_tracking"
down_revision = "003_compliance_framework"


def upgrade():
    # Add notes and resolution_notes columns to corrective_action
    op.add_column("corrective_action", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("corrective_action", sa.Column("resolution_notes", sa.Text(), nullable=True))

    # Create action_evidence table
    op.create_table(
        "action_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "action_id",
            sa.Integer(),
            sa.ForeignKey("corrective_action.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column(
            "uploaded_by_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("action_evidence")
    op.drop_column("corrective_action", "resolution_notes")
    op.drop_column("corrective_action", "notes")
