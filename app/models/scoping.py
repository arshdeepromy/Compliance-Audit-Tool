"""Scoping models — ScopingQuestion, ScopingRule, ScopingProfile, CriterionApplicability."""

from app.extensions import db


class ScopingQuestion(db.Model):
    """A scoping question defined on a framework template."""

    __tablename__ = "scoping_question"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("audit_template.id"), nullable=False
    )
    identifier = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_type = db.Column(db.String(20), nullable=False)
    options_json = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("template_id", "identifier"),
    )

    # Relationships
    template = db.relationship(
        "AuditTemplate", backref=db.backref("scoping_questions", lazy="dynamic"),
    )
    rules = db.relationship(
        "ScopingRule",
        backref="question",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    scoping_profiles = db.relationship(
        "ScopingProfile", backref="question", lazy="dynamic"
    )
    criterion_applicabilities = db.relationship(
        "CriterionApplicability", backref="scoped_by_question", lazy="dynamic"
    )

    def __repr__(self):
        return f"<ScopingQuestion {self.identifier}: {self.question_text[:40]}>"


class ScopingRule(db.Model):
    """A conditional rule linking a scoping question answer to criterion applicability."""

    __tablename__ = "scoping_rule"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("scoping_question.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_answer = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_code = db.Column(db.String(200), nullable=False)
    applicability_status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<ScopingRule question={self.question_id} trigger={self.trigger_answer}>"


class ScopingProfile(db.Model):
    """Persisted scoping answer for a single question within an audit."""

    __tablename__ = "scoping_profile"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(
        db.Integer,
        db.ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("scoping_question.id"), nullable=False
    )
    answer_value = db.Column(db.String(200), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("audit_id", "question_id"),
    )

    # Relationships
    audit = db.relationship(
        "Audit",
        backref=db.backref(
            "scoping_profiles", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    def __repr__(self):
        return f"<ScopingProfile audit={self.audit_id} question={self.question_id}>"


class CriterionApplicability(db.Model):
    """Tracks whether a criterion is applicable for a given audit based on scoping."""

    __tablename__ = "criterion_applicability"

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(
        db.Integer,
        db.ForeignKey("audit.id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion_id = db.Column(
        db.Integer, db.ForeignKey("template_criterion.id"), nullable=False
    )
    applicability_status = db.Column(db.String(20), nullable=False)
    scoped_by_question_id = db.Column(
        db.Integer, db.ForeignKey("scoping_question.id"), nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint("audit_id", "criterion_id"),
    )

    # Relationships
    audit = db.relationship(
        "Audit",
        backref=db.backref(
            "criterion_applicabilities", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )
    criterion = db.relationship("TemplateCriterion", backref="applicabilities")

    def __repr__(self):
        return f"<CriterionApplicability audit={self.audit_id} criterion={self.criterion_id}>"
