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
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    assigned_to = db.relationship(
        "User", foreign_keys=[assigned_to_id], backref="assigned_actions"
    )
    completed_by = db.relationship(
        "User", foreign_keys=[completed_by_id], backref="completed_actions"
    )

    def __repr__(self):
        return f"<CorrectiveAction {self.id} {self.criterion_code} status={self.status}>"
