"""Add compliance framework metadata and scoping tables.

Revision ID: 003_compliance_framework
Revises: 002_passkey_dual_mfa
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003_compliance_framework"
down_revision = "002_passkey_dual_mfa"
branch_labels = None
depends_on = None


def upgrade():
    # Add metadata columns to audit_template
    with op.batch_alter_table("audit_template") as batch_op:
        batch_op.add_column(sa.Column("domain_type", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column("compliance_framework", sa.String(200), nullable=True)
        )

    # Scoping question table
    op.create_table(
        "scoping_question",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("audit_template.id"),
            nullable=False,
        ),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(20), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("template_id", "identifier"),
    )

    # Scoping rule table
    op.create_table(
        "scoping_rule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("scoping_question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger_answer", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_code", sa.String(200), nullable=False),
        sa.Column("applicability_status", sa.String(20), nullable=False),
    )

    # Scoping profile table
    op.create_table(
        "scoping_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("scoping_question.id"),
            nullable=False,
        ),
        sa.Column("answer_value", sa.String(200), nullable=False),
        sa.UniqueConstraint("audit_id", "question_id"),
    )

    # Criterion applicability table
    op.create_table(
        "criterion_applicability",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "audit_id",
            sa.Integer(),
            sa.ForeignKey("audit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "criterion_id",
            sa.Integer(),
            sa.ForeignKey("template_criterion.id"),
            nullable=False,
        ),
        sa.Column("applicability_status", sa.String(20), nullable=False),
        sa.Column(
            "scoped_by_question_id",
            sa.Integer(),
            sa.ForeignKey("scoping_question.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("audit_id", "criterion_id"),
    )


def downgrade():
    op.drop_table("criterion_applicability")
    op.drop_table("scoping_profile")
    op.drop_table("scoping_rule")
    op.drop_table("scoping_question")
    with op.batch_alter_table("audit_template") as batch_op:
        batch_op.drop_column("compliance_framework")
        batch_op.drop_column("domain_type")
