"""Enterprise Risk Management models — ISO 31000 aligned.

Tables:
    RiskCategory   — Business areas (H&S, IT Security, Privacy, etc.)
    Risk           — Individual risk entries with likelihood/impact scoring
    RiskMitigation — Controls and treatments linked to risks
    RiskReview     — Periodic review log entries
"""

from datetime import datetime

from app.extensions import db


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

RISK_STATUSES = ("Open", "Mitigating", "Monitoring", "Closed", "Accepted")
TREATMENT_TYPES = ("Avoid", "Reduce", "Transfer", "Accept")
LIKELIHOOD_LABELS = {1: "Rare", 2: "Unlikely", 3: "Possible", 4: "Likely", 5: "Almost Certain"}
IMPACT_LABELS = {1: "Insignificant", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Catastrophic"}


def risk_level(score: int) -> str:
    """Return risk level string from a likelihood × impact score."""
    if score is None:
        return "Unrated"
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Medium"
    if score <= 15:
        return "High"
    return "Critical"


def risk_level_colour(score: int) -> str:
    """Return CSS colour for a risk level."""
    if score is None:
        return "#64748b"
    if score <= 4:
        return "#22c55e"
    if score <= 9:
        return "#eab308"
    if score <= 15:
        return "#f97316"
    return "#ef4444"


class RiskCategory(db.Model):
    """A business area for grouping risks (e.g. Health & Safety, IT Security)."""

    __tablename__ = "risk_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(10), nullable=True)  # emoji icon
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    risks = db.relationship("Risk", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<RiskCategory {self.name}>"


class Risk(db.Model):
    """An individual risk entry with inherent and residual scoring."""

    __tablename__ = "risk"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("risk_category.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    risk_source = db.Column(db.String(200), nullable=True)  # where the risk originates

    # Inherent risk (before controls)
    inherent_likelihood = db.Column(db.Integer, nullable=True)  # 1-5
    inherent_impact = db.Column(db.Integer, nullable=True)      # 1-5

    # Residual risk (after controls)
    residual_likelihood = db.Column(db.Integer, nullable=True)  # 1-5
    residual_impact = db.Column(db.Integer, nullable=True)      # 1-5

    status = db.Column(db.String(20), nullable=False, default="Open")
    treatment_type = db.Column(db.String(20), nullable=True)  # Avoid/Reduce/Transfer/Accept

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    review_frequency_days = db.Column(db.Integer, nullable=True, default=90)
    next_review_date = db.Column(db.Date, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_risks")
    created_by = db.relationship("User", foreign_keys=[created_by_id], backref="created_risks")
    mitigations = db.relationship("RiskMitigation", backref="risk", lazy="dynamic", cascade="all, delete-orphan")
    reviews = db.relationship("RiskReview", backref="risk", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def inherent_score(self):
        if self.inherent_likelihood and self.inherent_impact:
            return self.inherent_likelihood * self.inherent_impact
        return None

    @property
    def residual_score(self):
        if self.residual_likelihood and self.residual_impact:
            return self.residual_likelihood * self.residual_impact
        return None

    @property
    def inherent_level(self):
        return risk_level(self.inherent_score)

    @property
    def residual_level(self):
        return risk_level(self.residual_score)

    def __repr__(self):
        return f"<Risk {self.id} '{self.title[:40]}'>"


class RiskMitigation(db.Model):
    """A control or treatment action linked to a risk."""

    __tablename__ = "risk_mitigation"

    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    control_type = db.Column(db.String(30), nullable=True)  # Preventive/Detective/Corrective
    status = db.Column(db.String(20), nullable=False, default="Planned")  # Planned/In Progress/Implemented
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id], backref="assigned_mitigations")

    def __repr__(self):
        return f"<RiskMitigation {self.id} risk={self.risk_id}>"


class RiskReview(db.Model):
    """A periodic review log entry for a risk."""

    __tablename__ = "risk_review"

    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk.id"), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    review_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    previous_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)

    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id], backref="risk_reviews")

    def __repr__(self):
        return f"<RiskReview {self.id} risk={self.risk_id}>"
