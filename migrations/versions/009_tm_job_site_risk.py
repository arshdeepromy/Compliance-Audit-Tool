"""Traffic Management Job Site Risk tables.

Revision ID: 009_tm_job_site_risk
Revises: 008_risk_management
"""

from alembic import op
import sqlalchemy as sa

revision = "009_tm_job_site_risk"
down_revision = "008_risk_management"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tm_risk_subject",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tm_risk_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("tm_risk_subject.id"), nullable=False),
        sa.Column("code", sa.String(15), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("likelihood", sa.SmallInteger(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=True),
        sa.Column("causes", sa.JSON(), nullable=True),
        sa.Column("consequences", sa.JSON(), nullable=True),
        sa.Column("legislation", sa.JSON(), nullable=True),
        sa.Column("emergency_action", sa.Text(), nullable=True),
        sa.Column("copttm_ref", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tm_risk_template_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("tm_risk_template.id"), nullable=False),
        sa.Column("hierarchy", sa.String(20), nullable=False),
        sa.Column("control", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "tm_job_site",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_number", sa.String(50), nullable=True),
        sa.Column("site_name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("suburb", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("gps_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("gps_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("rca_name", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("speed_limit_kmh", sa.Integer(), nullable=True),
        sa.Column("work_zone_speed_kmh", sa.Integer(), nullable=True),
        sa.Column("includes_night_works", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("includes_motorway", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stms_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tm_job_site_subject",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_site_id", sa.Integer(), sa.ForeignKey("tm_job_site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("tm_risk_subject.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.UniqueConstraint("job_site_id", "subject_id"),
    )

    op.create_table(
        "tm_job_site_risk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_site_id", sa.Integer(), sa.ForeignKey("tm_job_site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("tm_risk_subject.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("tm_risk_template.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("likelihood", sa.SmallInteger(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=True),
        sa.Column("residual_likelihood", sa.SmallInteger(), nullable=True),
        sa.Column("residual_severity", sa.SmallInteger(), nullable=True),
        sa.Column("residual_risk_level", sa.String(10), nullable=True),
        sa.Column("causes", sa.JSON(), nullable=True),
        sa.Column("consequences", sa.JSON(), nullable=True),
        sa.Column("legislation", sa.JSON(), nullable=True),
        sa.Column("emergency_action", sa.Text(), nullable=True),
        sa.Column("copttm_ref", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Open"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tm_job_site_risk_control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_site_risk_id", sa.Integer(), sa.ForeignKey("tm_job_site_risk.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_control_id", sa.Integer(), sa.ForeignKey("tm_risk_template_control.id"), nullable=True),
        sa.Column("hierarchy", sa.String(20), nullable=False),
        sa.Column("control", sa.Text(), nullable=False),
        sa.Column("is_implemented", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("implemented_by", sa.String(200), nullable=True),
        sa.Column("implemented_at", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("tm_job_site_risk_control")
    op.drop_table("tm_job_site_risk")
    op.drop_table("tm_job_site_subject")
    op.drop_table("tm_job_site")
    op.drop_table("tm_risk_template_control")
    op.drop_table("tm_risk_template")
    op.drop_table("tm_risk_subject")
