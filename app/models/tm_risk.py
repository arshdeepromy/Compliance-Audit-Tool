"""Traffic Management Job Site Risk models.

Separate from the ISO 31000 organisational risk register.
Tables: tm_risk_subject, tm_risk_template, tm_risk_template_control,
        tm_job_site, tm_job_site_subject, tm_job_site_risk, tm_job_site_risk_control
"""

from datetime import datetime, date

from app.extensions import db

# ---------------------------------------------------------------------------
# Enumerations / helpers
# ---------------------------------------------------------------------------

JOB_STATUSES = ("Draft", "Active", "Completed", "Cancelled")
SITE_RISK_STATUSES = ("Open", "Controlled", "Closed", "NA")
HIERARCHY_ORDER = ("Eliminate", "Substitute", "Isolate", "Engineer", "Admin", "PPE")

LIKELIHOOD_LABELS = {1: "Rare", 2: "Unlikely", 3: "Possible", 4: "Likely", 5: "Almost Certain"}
SEVERITY_LABELS = {1: "Negligible", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Catastrophic"}


def calc_risk_level(score):
    if score is None:
        return "Unrated"
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Medium"
    if score <= 15:
        return "High"
    return "Critical"


def risk_level_colour(score):
    if score is None:
        return "#64748b"
    if score <= 4:
        return "#22c55e"
    if score <= 9:
        return "#eab308"
    if score <= 15:
        return "#f97316"
    return "#ef4444"


# ---------------------------------------------------------------------------
# Lookup / Template tables (pre-seeded, admin-editable)
# ---------------------------------------------------------------------------

class TMRiskSubject(db.Model):
    """Master risk subject type (e.g. Live Traffic, Night Works)."""
    __tablename__ = "tm_risk_subject"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(10), nullable=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    templates = db.relationship("TMRiskTemplate", backref="subject", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def active_template_count(self):
        return self.templates.filter_by(is_active=True).count()

    def __repr__(self):
        return f"<TMRiskSubject {self.code}: {self.name}>"


class TMRiskTemplate(db.Model):
    """Master template risk per subject — copied to job sites."""
    __tablename__ = "tm_risk_template"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("tm_risk_subject.id"), nullable=False)
    code = db.Column(db.String(15), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    likelihood = db.Column(db.SmallInteger, nullable=False)
    severity = db.Column(db.SmallInteger, nullable=False)
    risk_level = db.Column(db.String(10), nullable=True)
    causes = db.Column(db.JSON, nullable=True)
    consequences = db.Column(db.JSON, nullable=True)
    legislation = db.Column(db.JSON, nullable=True)
    emergency_action = db.Column(db.Text, nullable=True)
    copttm_ref = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    controls = db.relationship("TMRiskTemplateControl", backref="template", lazy="dynamic",
                               order_by="TMRiskTemplateControl.sort_order", cascade="all, delete-orphan")

    @property
    def score(self):
        return self.likelihood * self.severity

    def __repr__(self):
        return f"<TMRiskTemplate {self.code}: {self.title[:40]}>"


class TMRiskTemplateControl(db.Model):
    """Control measure belonging to a template risk."""
    __tablename__ = "tm_risk_template_control"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("tm_risk_template.id"), nullable=False)
    hierarchy = db.Column(db.String(20), nullable=False)
    control = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<TMRiskTemplateControl {self.hierarchy}: {self.control[:40]}>"


# ---------------------------------------------------------------------------
# Job Site tables (user-created, editable)
# ---------------------------------------------------------------------------

class TMJobSite(db.Model):
    """A traffic management job/deployment at a location."""
    __tablename__ = "tm_job_site"

    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), nullable=True)
    site_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    suburb = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    gps_lat = db.Column(db.Numeric(9, 6), nullable=True)
    gps_lng = db.Column(db.Numeric(9, 6), nullable=True)
    client_name = db.Column(db.String(200), nullable=True)
    rca_name = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    speed_limit_kmh = db.Column(db.Integer, nullable=True)
    work_zone_speed_kmh = db.Column(db.Integer, nullable=True)
    includes_night_works = db.Column(db.Boolean, nullable=False, default=False)
    includes_motorway = db.Column(db.Boolean, nullable=False, default=False)
    stms_name = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship("User", foreign_keys=[created_by], backref="tm_job_sites")
    subjects = db.relationship("TMJobSiteSubject", backref="job_site", lazy="dynamic", cascade="all, delete-orphan")
    risks = db.relationship("TMJobSiteRisk", backref="job_site", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def risk_count(self):
        return self.risks.filter(TMJobSiteRisk.status != "NA").count()

    @property
    def control_completion_pct(self):
        all_risks = self.risks.filter(TMJobSiteRisk.status != "NA").all()
        total = 0
        done = 0
        for r in all_risks:
            for c in r.controls:
                total += 1
                if c.is_implemented:
                    done += 1
        return int((done / total * 100) if total else 0)

    def __repr__(self):
        return f"<TMJobSite {self.job_number}: {self.site_name}>"


class TMJobSiteSubject(db.Model):
    """M2M: which risk subjects are selected for a job site."""
    __tablename__ = "tm_job_site_subject"

    id = db.Column(db.Integer, primary_key=True)
    job_site_id = db.Column(db.Integer, db.ForeignKey("tm_job_site.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("tm_risk_subject.id"), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    subject = db.relationship("TMRiskSubject")
    adder = db.relationship("User", foreign_keys=[added_by])

    __table_args__ = (db.UniqueConstraint("job_site_id", "subject_id"),)

    def __repr__(self):
        return f"<TMJobSiteSubject job={self.job_site_id} subject={self.subject_id}>"


class TMJobSiteRisk(db.Model):
    """Actual risk for a specific job site — copied from template then editable."""
    __tablename__ = "tm_job_site_risk"

    id = db.Column(db.Integer, primary_key=True)
    job_site_id = db.Column(db.Integer, db.ForeignKey("tm_job_site.id", ondelete="CASCADE"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("tm_risk_subject.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("tm_risk_template.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    likelihood = db.Column(db.SmallInteger, nullable=False)
    severity = db.Column(db.SmallInteger, nullable=False)
    risk_level = db.Column(db.String(10), nullable=True)
    residual_likelihood = db.Column(db.SmallInteger, nullable=True)
    residual_severity = db.Column(db.SmallInteger, nullable=True)
    residual_risk_level = db.Column(db.String(10), nullable=True)
    causes = db.Column(db.JSON, nullable=True)
    consequences = db.Column(db.JSON, nullable=True)
    legislation = db.Column(db.JSON, nullable=True)
    emergency_action = db.Column(db.Text, nullable=True)
    copttm_ref = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Open")
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subject = db.relationship("TMRiskSubject")
    template = db.relationship("TMRiskTemplate")
    controls = db.relationship("TMJobSiteRiskControl", backref="risk", lazy="select",
                               order_by="TMJobSiteRiskControl.sort_order", cascade="all, delete-orphan")

    @property
    def inherent_score(self):
        return self.likelihood * self.severity

    @property
    def residual_score(self):
        if self.residual_likelihood and self.residual_severity:
            return self.residual_likelihood * self.residual_severity
        return None

    @property
    def controls_done(self):
        return sum(1 for c in self.controls if c.is_implemented)

    @property
    def controls_total(self):
        return len(self.controls)

    def __repr__(self):
        return f"<TMJobSiteRisk {self.id}: {self.title[:40]}>"


class TMJobSiteRiskControl(db.Model):
    """Control measure for a specific job site risk — editable copy."""
    __tablename__ = "tm_job_site_risk_control"

    id = db.Column(db.Integer, primary_key=True)
    job_site_risk_id = db.Column(db.Integer, db.ForeignKey("tm_job_site_risk.id", ondelete="CASCADE"), nullable=False)
    template_control_id = db.Column(db.Integer, db.ForeignKey("tm_risk_template_control.id"), nullable=True)
    hierarchy = db.Column(db.String(20), nullable=False)
    control = db.Column(db.Text, nullable=False)
    is_implemented = db.Column(db.Boolean, nullable=False, default=False)
    implemented_by = db.Column(db.String(200), nullable=True)
    implemented_at = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<TMJobSiteRiskControl {self.hierarchy}: {self.control[:40]}>"
