"""Audit template models — AuditTemplate, TemplateSection, TemplateCriterion,
CriterionScoringAnchor, CriterionEvidenceItem."""

from datetime import datetime

from app.extensions import db


class AuditTemplate(db.Model):
    """Reusable audit template definition (e.g. Tōtika Category 2)."""

    __tablename__ = "audit_template"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)
    domain_type = db.Column(db.String(100), nullable=True)
    compliance_framework = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    sections = db.relationship(
        "TemplateSection",
        backref="template",
        lazy="dynamic",
        order_by="TemplateSection.sort_order",
        cascade="all, delete-orphan",
    )
    audits = db.relationship("Audit", backref="template", lazy="dynamic")

    def __repr__(self):
        return f"<AuditTemplate {self.name} v{self.version}>"


class TemplateSection(db.Model):
    """A section within an audit template containing criteria."""

    __tablename__ = "template_section"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("audit_template.id"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)

    # Relationships
    criteria = db.relationship(
        "TemplateCriterion",
        backref="section",
        lazy="dynamic",
        order_by="TemplateCriterion.sort_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TemplateSection {self.name}>"


class TemplateCriterion(db.Model):
    """A single auditable criterion within a template section."""

    __tablename__ = "template_criterion"

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(
        db.Integer, db.ForeignKey("template_section.id"), nullable=False
    )
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    guidance = db.Column(db.Text, nullable=True)
    question = db.Column(db.Text, nullable=True)
    na_allowed = db.Column(db.Boolean, default=False, nullable=False)
    info_only = db.Column(db.Boolean, default=False, nullable=False)
    tip = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False)

    # Relationships
    scoring_anchors = db.relationship(
        "CriterionScoringAnchor",
        backref="criterion",
        lazy="dynamic",
        order_by="CriterionScoringAnchor.score",
        cascade="all, delete-orphan",
    )
    evidence_items = db.relationship(
        "CriterionEvidenceItem",
        backref="criterion",
        lazy="dynamic",
        order_by="CriterionEvidenceItem.sort_order",
        cascade="all, delete-orphan",
    )
    audit_scores = db.relationship("AuditScore", backref="criterion", lazy="dynamic")

    def __repr__(self):
        return f"<TemplateCriterion {self.code}: {self.title}>"


class CriterionScoringAnchor(db.Model):
    """Score anchor description for a criterion (one per score level 0–4)."""

    __tablename__ = "criterion_scoring_anchor"

    id = db.Column(db.Integer, primary_key=True)
    criterion_id = db.Column(
        db.Integer, db.ForeignKey("template_criterion.id"), nullable=False
    )
    score = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<CriterionScoringAnchor criterion={self.criterion_id} score={self.score}>"


class CriterionEvidenceItem(db.Model):
    """An evidence checklist item for a criterion."""

    __tablename__ = "criterion_evidence_item"

    id = db.Column(db.Integer, primary_key=True)
    criterion_id = db.Column(
        db.Integer, db.ForeignKey("template_criterion.id"), nullable=False
    )
    text = db.Column(db.Text, nullable=False)
    age_label = db.Column(db.String(50), nullable=True)
    age_class = db.Column(db.String(20), nullable=True)
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)

    # Relationships
    check_states = db.relationship(
        "EvidenceCheckState", backref="evidence_item", lazy="dynamic"
    )

    def __repr__(self):
        return f"<CriterionEvidenceItem criterion={self.criterion_id}>"
