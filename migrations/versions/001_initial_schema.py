"""Initial schema — all 16 tables.

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- User & Session ---
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(80), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("roles", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("mfa_type", sa.String(20), nullable=True),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )

    # --- Audit Template hierarchy ---
    op.create_table(
        "audit_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "template_section",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("audit_template.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )

    op.create_table(
        "template_criterion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "section_id",
            sa.Integer(),
            sa.ForeignKey("template_section.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("guidance", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("na_allowed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("tip", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )

    op.create_table(
        "criterion_scoring_anchor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "criterion_id",
            sa.Integer(),
            sa.ForeignKey("template_criterion.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )

    op.create_table(
        "criterion_evidence_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "criterion_id",
            sa.Integer(),
            sa.ForeignKey("template_criterion.id"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("age_label", sa.String(50), nullable=True),
        sa.Column("age_class", sa.String(20), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )

    # --- Audit lifecycle ---
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("audit_template.id"),
            nullable=False,
        ),
        sa.Column(
            "auditor_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False
        ),
        sa.Column(
            "auditee_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("audit_date", sa.Date(), nullable=True),
        sa.Column("assessment_period", sa.String(100), nullable=True),
        sa.Column("next_review_due", sa.Date(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("imported_from", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "audit_score",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_id", sa.Integer(), sa.ForeignKey("audit.id"), nullable=False
        ),
        sa.Column(
            "criterion_id",
            sa.Integer(),
            sa.ForeignKey("template_criterion.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("is_na", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("na_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "evidence_check_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_score_id",
            sa.Integer(),
            sa.ForeignKey("audit_score.id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_item_id",
            sa.Integer(),
            sa.ForeignKey("criterion_evidence_item.id"),
            nullable=False,
        ),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.create_table(
        "audit_sign_off",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_id", sa.Integer(), sa.ForeignKey("audit.id"), nullable=False
        ),
        sa.Column("auditor_finalised_at", sa.DateTime(), nullable=True),
        sa.Column("auditee_acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("auditee_typed_name", sa.String(200), nullable=True),
        sa.Column("auditee_comments", sa.Text(), nullable=True),
    )

    # --- Corrective actions ---
    op.create_table(
        "corrective_action",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_id", sa.Integer(), sa.ForeignKey("audit.id"), nullable=False
        ),
        sa.Column("criterion_code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "assigned_to_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Open"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "completed_by_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # --- Evidence attachments ---
    op.create_table(
        "evidence_attachment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_score_id",
            sa.Integer(),
            sa.ForeignKey("audit_score.id"),
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

    # --- Settings singletons ---
    op.create_table(
        "branding_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_name",
            sa.String(200),
            nullable=False,
            server_default="Tōtika Audit Tool",
        ),
        sa.Column("logo_filename", sa.String(255), nullable=True),
        sa.Column(
            "primary_colour", sa.String(7), nullable=False, server_default="#f97316"
        ),
        sa.Column(
            "accent_colour", sa.String(7), nullable=False, server_default="#fb923c"
        ),
    )

    op.create_table(
        "smtp_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("sender_address", sa.String(255), nullable=True),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default="1"),
    )

    # --- Activity log ---
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )

    # --- Seed file tracker ---
    op.create_table(
        "seed_file_tracker",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), unique=True, nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column(
            "audit_id", sa.Integer(), sa.ForeignKey("audit.id"), nullable=True
        ),
    )


def downgrade():
    op.drop_table("seed_file_tracker")
    op.drop_table("activity_log")
    op.drop_table("smtp_settings")
    op.drop_table("branding_settings")
    op.drop_table("evidence_attachment")
    op.drop_table("corrective_action")
    op.drop_table("audit_sign_off")
    op.drop_table("evidence_check_state")
    op.drop_table("audit_score")
    op.drop_table("audit")
    op.drop_table("criterion_evidence_item")
    op.drop_table("criterion_scoring_anchor")
    op.drop_table("template_criterion")
    op.drop_table("template_section")
    op.drop_table("audit_template")
    op.drop_table("session")
    op.drop_table("user")
