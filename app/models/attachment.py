"""Evidence attachment model."""

from datetime import datetime

from app.extensions import db


class EvidenceAttachment(db.Model):
    """A file uploaded as supporting evidence for a criterion score."""

    __tablename__ = "evidence_attachment"

    id = db.Column(db.Integer, primary_key=True)
    audit_score_id = db.Column(
        db.Integer, db.ForeignKey("audit_score.id"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    uploaded_by = db.relationship("User", backref="uploaded_attachments")

    def __repr__(self):
        return f"<EvidenceAttachment {self.original_filename}>"
