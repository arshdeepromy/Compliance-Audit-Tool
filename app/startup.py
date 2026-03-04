"""Startup tasks: run migrations, seed default data."""

import logging

import bcrypt
from alembic import command
from alembic.config import Config as AlembicConfig

from app.extensions import db
from app.models.user import User, UserPasskey
from app.models.settings import BrandingSettings, SMTPSettings
from app.models.template import (
    AuditTemplate,
    TemplateSection,
    TemplateCriterion,
    CriterionScoringAnchor,
    CriterionEvidenceItem,
)

logger = logging.getLogger(__name__)


def run_migrations(app):
    """Apply any pending Alembic migrations."""
    import os

    alembic_ini = os.path.join(os.path.dirname(app.root_path), "alembic.ini")
    alembic_cfg = AlembicConfig(alembic_ini)
    # Point script_location to the migrations directory next to alembic.ini
    alembic_cfg.set_main_option(
        "script_location",
        os.path.join(os.path.dirname(app.root_path), "migrations"),
    )
    # Override the sqlalchemy.url with the app's configured URI
    alembic_cfg.set_main_option(
        "sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"]
    )

    with app.app_context():
        command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied.")


def seed_default_admin(app):
    """Create the default admin account if it doesn't already exist."""
    with app.app_context():
        existing = User.query.filter_by(username="admin").first()
        if existing is not None:
            return

        password = app.config.get("DEFAULT_ADMIN_PASSWORD", "admin")
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        admin = User(
            username="admin",
            email="admin@localhost",
            display_name="Administrator",
            password_hash=password_hash,
            roles="admin",
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        logger.info("Default admin account created.")


def seed_branding_defaults(app):
    """Create the BrandingSettings singleton with defaults if it doesn't exist."""
    with app.app_context():
        existing = db.session.get(BrandingSettings, 1)
        if existing is not None:
            return

        branding = BrandingSettings(
            id=1,
            company_name="Tōtika Audit Tool",
            primary_colour="#f97316",
            accent_colour="#fb923c",
        )
        db.session.add(branding)
        db.session.commit()
        logger.info("Default branding settings seeded.")


def seed_smtp_defaults(app):
    """Create the SMTPSettings singleton with defaults if it doesn't exist."""
    with app.app_context():
        existing = db.session.get(SMTPSettings, 1)
        if existing is not None:
            return

        smtp = SMTPSettings(
            id=1,
            port=587,
            use_tls=True,
        )
        db.session.add(smtp)
        db.session.commit()
        logger.info("Default SMTP settings seeded.")


def seed_totika_template(app):
    """Seed the built-in Tōtika Category 2 template if it doesn't already exist.

    Idempotent — checks for an existing built-in template by name before creating.
    """
    from app.seed_data.totika_cat2 import (
        TEMPLATE_NAME,
        TEMPLATE_VERSION,
        SECTIONS,
        CRITERIA,
    )

    with app.app_context():
        existing = AuditTemplate.query.filter_by(
            name=TEMPLATE_NAME, is_builtin=True
        ).first()
        if existing is not None:
            logger.info("Built-in Tōtika template already exists (id=%s).", existing.id)
            return

        template = AuditTemplate(
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            description="Tōtika Core Criteria v3.1.4 — Category 2 Suppliers (MB1–MB54)",
            is_active=True,
            is_builtin=True,
        )
        db.session.add(template)
        db.session.flush()  # get template.id

        criterion_sort = 0
        for section_order, section_data in enumerate(SECTIONS):
            section = TemplateSection(
                template_id=template.id,
                name=section_data["name"],
                sort_order=section_order,
            )
            db.session.add(section)
            db.session.flush()  # get section.id

            for code in section_data["codes"]:
                crit_data = CRITERIA[code]
                criterion_sort += 1

                criterion = TemplateCriterion(
                    section_id=section.id,
                    code=code,
                    title=crit_data["title"],
                    guidance=crit_data.get("guidance") or None,
                    question=crit_data.get("question") or None,
                    na_allowed=crit_data.get("na_allowed", False),
                    tip=crit_data.get("tip") or None,
                    sort_order=criterion_sort,
                )
                db.session.add(criterion)
                db.session.flush()  # get criterion.id

                # Scoring anchors (0–4)
                for anchor in crit_data.get("scoring", []):
                    db.session.add(
                        CriterionScoringAnchor(
                            criterion_id=criterion.id,
                            score=anchor["score"],
                            description=anchor["description"],
                        )
                    )

                # Evidence checklist items
                for ev_order, ev in enumerate(crit_data.get("evidence", [])):
                    db.session.add(
                        CriterionEvidenceItem(
                            criterion_id=criterion.id,
                            text=ev["text"],
                            age_label=ev.get("age_label"),
                            age_class=ev.get("age_class"),
                            is_required=ev.get("required", False),
                            sort_order=ev_order,
                        )
                    )

        db.session.commit()
        logger.info(
            "Seeded built-in Tōtika Category 2 template (id=%s) with %d criteria.",
            template.id,
            criterion_sort,
        )


def run_startup_tasks(app):
    """Execute all startup tasks in order: migrations → seeding → scheduler."""
    run_migrations(app)
    seed_default_admin(app)
    seed_branding_defaults(app)
    seed_smtp_defaults(app)
    seed_totika_template(app)

    # Import seed data from seed_data/ directory (Req 17.5, 17.6, 17.7)
    from app.services.importer import load_seed_data

    with app.app_context():
        try:
            load_seed_data(app)
        except Exception as exc:
            logger.warning("Seed data loading failed: %s", exc)

    # Run scheduler checks on startup
    from app.services.scheduler import check_reminders, check_overdue_actions

    with app.app_context():
        try:
            check_overdue_actions()
            check_reminders()
        except Exception as exc:
            logger.warning("Startup scheduler checks failed: %s", exc)
