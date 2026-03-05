"""Corrective action model."""

from datetime import datetime

from app.extensions import db


# Valid corrective action status values
ACTION_STATUSES = ("Open", "In_Progress", "Completed", "Overdue")


class CorrectiveAction(db.Model):
    """A tracked remediation task for a gap item."""

    __tablename__ = "corrective_action"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey("audit.id"), nullable=False)
    criterion_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open")
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Rich gap-item fields (from legacy JSON gapItems)
    gap_item_id = db.Column(db.String(20), nullable=True)       # e.g. "G001"
    title = db.Column(db.Text, nullable=True)                    # short title
    action_text = db.Column(db.Text, nullable=True)              # "What to do"
    form_or_doc = db.Column(db.String(500), nullable=True)       # document/form required
    quantity = db.Column(db.String(255), nullable=True)           # quantity required
    max_age = db.Column(db.String(255), nullable=True)           # human-readable max age
    max_age_months = db.Column(db.Integer, nullable=True)         # numeric max age in months
    signed = db.Column(db.Boolean, nullable=True)                 # signature required?
    signed_by = db.Column(db.String(500), nullable=True)          # who must sign
    category = db.Column(db.String(100), nullable=True)           # e.g. "Training", "Leadership"
    criteria_codes = db.Column(db.Text, nullable=True)            # comma-separated criteria codes

    # Relationships
    assigned_to = db.relationship(
        "User", foreign_keys=[assigned_to_id], backref="assigned_actions"
    )
    completed_by = db.relationship(
        "User", foreign_keys=[completed_by_id], backref="completed_actions"
    )
    evidence_files = db.relationship(
        "ActionEvidence", backref="action", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CorrectiveAction {self.id} {self.criterion_code} status={self.status}>"


class ActionEvidence(db.Model):
    """A file uploaded as evidence for closing a corrective action."""

    __tablename__ = "action_evidence"

    id = db.Column(db.Integer, primary_key=True)
    action_id = db.Column(
        db.Integer, db.ForeignKey("corrective_action.id"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    uploaded_by = db.relationship("User", backref="action_evidence_uploads")

    def __repr__(self):
        return f"<ActionEvidence {self.original_filename}>"
