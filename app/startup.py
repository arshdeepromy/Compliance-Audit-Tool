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
    """Apply any pending Alembic migrations.

    Safety: logs the DB file size before and after to detect data loss.
    """
    import os

    # Log DB state before migrations
    db_path = app.config.get("SQLALCHEMY_DATABASE_URI", "").replace("sqlite:///", "")
    pre_size = 0
    if db_path and os.path.isfile(db_path):
        pre_size = os.path.getsize(db_path)
        logger.info("Database before migration: %s (%d bytes)", db_path, pre_size)
    else:
        logger.info("No existing database found — fresh install at %s", db_path)

    alembic_ini = os.path.join(os.path.dirname(app.root_path), "alembic.ini")
    alembic_cfg = AlembicConfig(alembic_ini)
    alembic_cfg.set_main_option(
        "script_location",
        os.path.join(os.path.dirname(app.root_path), "migrations"),
    )
    alembic_cfg.set_main_option(
        "sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"]
    )

    with app.app_context():
        command.upgrade(alembic_cfg, "head")

    # Verify DB wasn't wiped by migration
    if db_path and os.path.isfile(db_path):
        post_size = os.path.getsize(db_path)
        logger.info("Database after migration: %d bytes", post_size)
        if pre_size > 10000 and post_size < (pre_size // 2):
            logger.error(
                "DATABASE SIZE DROPPED from %d to %d bytes after migration! "
                "Possible data loss detected.",
                pre_size,
                post_size,
            )
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
        TEMPLATE_METADATA,
        SECTIONS,
        CRITERIA,
    )

    with app.app_context():
        existing = AuditTemplate.query.filter_by(
            name=TEMPLATE_NAME, is_builtin=True
        ).first()
        if existing is not None:
            # Update metadata on existing template if missing
            changed = False
            if TEMPLATE_METADATA.get("domain_type") and not existing.domain_type:
                existing.domain_type = TEMPLATE_METADATA["domain_type"]
                changed = True
            if TEMPLATE_METADATA.get("compliance_framework") and not existing.compliance_framework:
                existing.compliance_framework = TEMPLATE_METADATA["compliance_framework"]
                changed = True
            if changed:
                db.session.commit()
                logger.info("Updated metadata on existing Tōtika template (id=%s).", existing.id)
            else:
                logger.info("Built-in Tōtika template already exists (id=%s).", existing.id)
            return

        template = AuditTemplate(
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            description="Tōtika Core Criteria v3.1.4 — Category 2 Suppliers (MB1–MB54)",
            is_active=True,
            is_builtin=True,
            domain_type=TEMPLATE_METADATA.get("domain_type"),
            compliance_framework=TEMPLATE_METADATA.get("compliance_framework"),
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
                    info_only=crit_data.get("info_only", False),
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


def seed_framework_template(app, module):
    """Seed a compliance framework template from a seed data module.

    Handles TEMPLATE_METADATA, SCOPING_QUESTIONS, and SCOPING_RULES in
    addition to the standard section/criteria seeding.  Idempotent — skips
    if a built-in template with the same name already exists.
    """
    from app.models.scoping import ScopingQuestion, ScopingRule

    name = module.TEMPLATE_NAME
    version = module.TEMPLATE_VERSION
    metadata = getattr(module, "TEMPLATE_METADATA", {})
    sections = module.SECTIONS
    criteria = module.CRITERIA
    scoping_questions = getattr(module, "SCOPING_QUESTIONS", [])
    scoping_rules = getattr(module, "SCOPING_RULES", [])

    with app.app_context():
        existing = AuditTemplate.query.filter_by(name=name, is_builtin=True).first()
        if existing is not None:
            # Update metadata on existing template if missing
            changed = False
            if metadata.get("domain_type") and not existing.domain_type:
                existing.domain_type = metadata["domain_type"]
                changed = True
            if metadata.get("compliance_framework") and not existing.compliance_framework:
                existing.compliance_framework = metadata["compliance_framework"]
                changed = True
            if changed:
                db.session.commit()
                logger.info("Updated metadata on existing template '%s'.", name)
            else:
                logger.info("Framework template '%s' already exists (id=%s).", name, existing.id)
            return

        template = AuditTemplate(
            name=name,
            version=version,
            description=f"{name} compliance framework template",
            is_active=True,
            is_builtin=True,
            domain_type=metadata.get("domain_type"),
            compliance_framework=metadata.get("compliance_framework"),
        )
        db.session.add(template)
        db.session.flush()

        criterion_sort = 0
        for section_order, section_data in enumerate(sections):
            section = TemplateSection(
                template_id=template.id,
                name=section_data["name"],
                sort_order=section_order,
            )
            db.session.add(section)
            db.session.flush()

            for code in section_data["codes"]:
                crit_data = criteria[code]
                criterion_sort += 1
                criterion = TemplateCriterion(
                    section_id=section.id,
                    code=code,
                    title=crit_data["title"],
                    guidance=crit_data.get("guidance"),
                    question=crit_data.get("question"),
                    na_allowed=crit_data.get("na_allowed", False),
                    info_only=crit_data.get("info_only", False),
                    tip=crit_data.get("tip"),
                    sort_order=criterion_sort,
                )
                db.session.add(criterion)
                db.session.flush()

                for anchor in crit_data.get("scoring", []):
                    db.session.add(
                        CriterionScoringAnchor(
                            criterion_id=criterion.id,
                            score=anchor["score"],
                            description=anchor["description"],
                        )
                    )
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

        # Seed scoping questions and rules
        question_map = {}  # identifier -> ScopingQuestion
        for sq in scoping_questions:
            q = ScopingQuestion(
                template_id=template.id,
                identifier=sq["identifier"],
                question_text=sq["question_text"],
                answer_type=sq["answer_type"],
                options_json=sq.get("options"),
                sort_order=sq["sort_order"],
            )
            db.session.add(q)
            db.session.flush()
            question_map[sq["identifier"]] = q

        for sr in scoping_rules:
            q = question_map.get(sr["question_identifier"])
            if q is None:
                logger.warning(
                    "Scoping rule references unknown question '%s' in template '%s'.",
                    sr["question_identifier"],
                    name,
                )
                continue
            db.session.add(
                ScopingRule(
                    question_id=q.id,
                    trigger_answer=sr["trigger_answer"],
                    target_type=sr["target_type"],
                    target_code=sr["target_code"],
                    applicability_status=sr["applicability_status"],
                )
            )

        db.session.commit()
        logger.info(
            "Seeded framework template '%s' (id=%s) with %d criteria, %d scoping questions.",
            name,
            template.id,
            criterion_sort,
            len(scoping_questions),
        )


def seed_all_framework_templates(app):
    """Seed all compliance framework templates."""
    from app.seed_data import pci_dss_v4, iso_27001, nist_csf_2
    from app.seed_data import iso_9001, iso_14001, iso_45001
    from app.seed_data import gdpr, soc2

    framework_modules = [
        pci_dss_v4,
        iso_27001,
        nist_csf_2,
        iso_9001,
        iso_14001,
        iso_45001,
        gdpr,
        soc2,
    ]

    for module in framework_modules:
        try:
            seed_framework_template(app, module)
        except Exception as exc:
            logger.warning(
                "Failed to seed framework template from %s: %s",
                module.__name__,
                exc,
            )


def seed_risk_categories(app):
    """Seed default enterprise risk categories if none exist."""
    from app.models.risk import RiskCategory

    DEFAULT_CATEGORIES = [
        {"name": "Health & Safety", "icon": "🛡️", "description": "Workplace health, safety, and wellbeing risks"},
        {"name": "IT Security", "icon": "🔒", "description": "Cybersecurity, data breaches, and IT infrastructure risks"},
        {"name": "Privacy & Data Protection", "icon": "🔐", "description": "Personal data handling, GDPR, and privacy compliance risks"},
        {"name": "Environmental", "icon": "🌿", "description": "Environmental impact, sustainability, and regulatory compliance"},
        {"name": "Financial", "icon": "💰", "description": "Financial loss, fraud, and economic risks"},
        {"name": "Operational", "icon": "⚙️", "description": "Business operations, supply chain, and process risks"},
        {"name": "Legal & Compliance", "icon": "⚖️", "description": "Legal liability, regulatory non-compliance, and contractual risks"},
        {"name": "Strategic", "icon": "🎯", "description": "Strategic planning, market changes, and competitive risks"},
        {"name": "Reputational", "icon": "📢", "description": "Brand damage, public perception, and stakeholder trust risks"},
        {"name": "Human Resources", "icon": "👥", "description": "Workforce, talent retention, and employment risks"},
    ]

    with app.app_context():
        existing = RiskCategory.query.first()
        if existing is not None:
            return

        for i, cat_data in enumerate(DEFAULT_CATEGORIES):
            cat = RiskCategory(
                name=cat_data["name"],
                description=cat_data["description"],
                icon=cat_data["icon"],
                sort_order=i,
            )
            db.session.add(cat)

        db.session.commit()
        logger.info("Seeded %d default risk categories.", len(DEFAULT_CATEGORIES))


def run_startup_tasks(app):
    """Execute all startup tasks in order: migrations → seeding → scheduler."""
    run_migrations(app)
    seed_default_admin(app)
    seed_branding_defaults(app)
    seed_smtp_defaults(app)
    seed_totika_template(app)
    seed_all_framework_templates(app)
    seed_risk_categories(app)

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
