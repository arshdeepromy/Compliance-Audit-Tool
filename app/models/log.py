"""Activity log and seed file tracker models."""

from datetime import datetime

from app.extensions import db


class ActivityLog(db.Model):
    """Immutable record of significant user and system actions."""

    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    def __repr__(self):
        return f"<ActivityLog {self.action} at {self.created_at}>"


class SeedFileTracker(db.Model):
    """Tracks imported seed files to prevent duplicate imports on restart."""

    __tablename__ = "seed_file_tracker"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    imported_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    audit_id = db.Column(db.Integer, db.ForeignKey("audit.id"), nullable=True)

    def __repr__(self):
        return f"<SeedFileTracker {self.filename}>"
