"""Audit lifecycle models — Audit, AuditScore, EvidenceCheckState, AuditSignOff."""

from datetime import datetime

from app.extensions import db


# Valid audit status values
AUDIT_STATUSES = ("Draft", "In_Progress", "Review", "Completed", "Archived")


class Audit(db.Model):
    """A single audit instance linked to a template and users."""

    __tablename__ = "audit"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("audit_template.id"), nullable=False
    )
    auditor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    auditee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    audit_date = db.Column(db.Date, nullable=True)
    assessment_period = db.Column(db.String(100), nullable=True)
    next_review_due = db.Column(db.Date, nullable=True)
    overall_score = db.Column(db.Float, nullable=True)
    imported_from = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    scores = db.relationship(
        "AuditScore", backref="audit", lazy="dynamic", cascade="all, delete-orphan"
    )
    corrective_actions = db.relationship(
        "CorrectiveAction", backref="audit", lazy="dynamic", cascade="all, delete-orphan"
    )
    sign_off = db.relationship(
        "AuditSignOff", backref="audit", uselist=False, cascade="all, delete-orphan"
    )
    seed_tracker = db.relationship(
        "SeedFileTracker", backref="audit", uselist=False
    )

    def __repr__(self):
        return f"<Audit {self.id} status={self.status}>"


class AuditScore(db.Model):
    """Score record for a single criterion within an audit."""

    __tablename__ = "audit_score"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey("audit.id"), nullable=False)
    criterion_id = db.Column(
        db.Integer, db.ForeignKey("template_criterion.id"), nullable=False
    )
    score = db.Column(db.Integer, nullable=True)
    is_na = db.Column(db.Boolean, default=False, nullable=False)
    na_reason = db.Column(db.Text, nullable=True)
    info_answer = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    evidence_check_states = db.relationship(
        "EvidenceCheckState",
        backref="audit_score",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attachments = db.relationship(
        "EvidenceAttachment",
        backref="audit_score",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<AuditScore audit={self.audit_id} criterion={self.criterion_id} score={self.score}>"


class EvidenceCheckState(db.Model):
    """Tracks whether an evidence checklist item has been checked for a score."""

    __tablename__ = "evidence_check_state"

    id = db.Column(db.Integer, primary_key=True)
    audit_score_id = db.Column(
        db.Integer, db.ForeignKey("audit_score.id"), nullable=False
    )
    evidence_item_id = db.Column(
        db.Integer, db.ForeignKey("criterion_evidence_item.id"), nullable=False
    )
    is_checked = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<EvidenceCheckState score={self.audit_score_id} item={self.evidence_item_id}>"


class AuditSignOff(db.Model):
    """Sign-off record for auditor finalisation and auditee acknowledgement."""

    __tablename__ = "audit_sign_off"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey("audit.id"), nullable=False)
    auditor_finalised_at = db.Column(db.DateTime, nullable=True)
    auditee_acknowledged_at = db.Column(db.DateTime, nullable=True)
    auditee_typed_name = db.Column(db.String(200), nullable=True)
    auditee_comments = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<AuditSignOff audit={self.audit_id}>"
