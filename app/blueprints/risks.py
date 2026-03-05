"""Enterprise Risk Management blueprint — ISO 31000 aligned.

Routes:
    GET  /risks                    — Risk register (filterable list)
    GET  /risks/matrix             — 5×5 risk heatmap
    GET  /risks/new                — Add risk form
    POST /risks/new                — Create risk
    GET  /risks/<id>               — Risk detail with mitigations
    GET  /risks/<id>/edit          — Edit risk form
    POST /risks/<id>/edit          — Update risk
    POST /risks/<id>/mitigations   — Add mitigation
    POST /risks/<id>/review        — Log a review
    POST /risks/<id>/delete        — Delete risk
    POST /risks/mitigations/<mid>/status — Update mitigation status
"""

from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.extensions import db
from app.models.risk import (
    IMPACT_LABELS,
    LIKELIHOOD_LABELS,
    RISK_STATUSES,
    TREATMENT_TYPES,
    Risk,
    RiskCategory,
    RiskMitigation,
    RiskReview,
    risk_level,
    risk_level_colour,
)
from app.models.user import User
from app.utils.rbac import login_required, roles_required

risks_bp = Blueprint("risks", __name__)


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def _risk_context():
    """Common template context for risk pages."""
    return dict(
        statuses=RISK_STATUSES,
        treatment_types=TREATMENT_TYPES,
        likelihood_labels=LIKELIHOOD_LABELS,
        impact_labels=IMPACT_LABELS,
        risk_level=risk_level,
        risk_level_colour=risk_level_colour,
        categories=RiskCategory.query.filter_by(is_active=True).order_by(RiskCategory.sort_order).all(),
        users=User.query.filter_by(is_active=True).order_by(User.display_name).all(),
    )


# ---------------------------------------------------------------------------
# Risk Register
# ---------------------------------------------------------------------------

@risks_bp.route("/risks")
@login_required
def risk_register():
    """Main risk register — filterable by category, status, level."""
    ctx = _risk_context()
    query = Risk.query

    # Filters
    cat_id = request.args.get("category", type=int)
    status = request.args.get("status")
    level = request.args.get("level")

    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if status:
        query = query.filter_by(status=status)

    risks = query.order_by(Risk.created_at.desc()).all()

    # Post-filter by level (computed property)
    if level:
        risks = [r for r in risks if r.inherent_level == level]

    # Summary stats
    total = len(risks)
    critical = sum(1 for r in risks if r.inherent_level == "Critical")
    high = sum(1 for r in risks if r.inherent_level == "High")
    medium = sum(1 for r in risks if r.inherent_level == "Medium")
    low = sum(1 for r in risks if r.inherent_level == "Low")
    open_count = sum(1 for r in risks if r.status == "Open")
    overdue_reviews = sum(1 for r in risks if r.next_review_date and r.next_review_date < date.today())

    return render_template(
        "risk/register.html",
        risks=risks,
        total=total, critical=critical, high=high, medium=medium, low=low,
        open_count=open_count, overdue_reviews=overdue_reviews,
        filter_category=cat_id, filter_status=status, filter_level=level,
        today=date.today(),
        **ctx,
    )


# ---------------------------------------------------------------------------
# Risk Matrix (5×5 Heatmap)
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/matrix")
@login_required
def risk_matrix():
    """5×5 risk heatmap view."""
    ctx = _risk_context()
    risks = Risk.query.all()

    # Build matrix: matrix[likelihood][impact] = [list of risks]
    matrix = {}
    for li in range(1, 6):
        matrix[li] = {}
        for im in range(1, 6):
            matrix[li][im] = []

    for r in risks:
        if r.inherent_likelihood and r.inherent_impact:
            matrix[r.inherent_likelihood][r.inherent_impact].append(r)

    return render_template(
        "risk/matrix.html",
        risks=risks, matrix=matrix,
        **ctx,
    )


# ---------------------------------------------------------------------------
# Add / Edit Risk
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/new", methods=["GET", "POST"])
@roles_required("admin", "auditor")
def add_risk():
    """Create a new risk."""
    ctx = _risk_context()
    if request.method == "POST":
        risk = Risk(
            category_id=request.form.get("category_id", type=int),
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip() or None,
            risk_source=request.form.get("risk_source", "").strip() or None,
            inherent_likelihood=request.form.get("inherent_likelihood", type=int),
            inherent_impact=request.form.get("inherent_impact", type=int),
            residual_likelihood=request.form.get("residual_likelihood", type=int),
            residual_impact=request.form.get("residual_impact", type=int),
            status=request.form.get("status", "Open"),
            treatment_type=request.form.get("treatment_type") or None,
            owner_id=request.form.get("owner_id", type=int) or None,
            due_date=_parse_date(request.form.get("due_date")),
            review_frequency_days=request.form.get("review_frequency_days", type=int) or 90,
            created_by_id=g.current_user.id,
        )
        # Set next review date
        risk.next_review_date = date.today() + timedelta(days=risk.review_frequency_days)
        db.session.add(risk)
        db.session.commit()
        flash("Risk created successfully.", "success")
        return redirect(url_for("risks.risk_detail", risk_id=risk.id))

    return render_template("risk/form.html", risk=None, mode="add", **ctx)


@risks_bp.route("/risks/<int:risk_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "auditor")
def edit_risk(risk_id):
    """Edit an existing risk."""
    risk = db.session.get(Risk, risk_id)
    if not risk:
        abort(404)
    ctx = _risk_context()

    if request.method == "POST":
        risk.category_id = request.form.get("category_id", type=int)
        risk.title = request.form.get("title", "").strip()
        risk.description = request.form.get("description", "").strip() or None
        risk.risk_source = request.form.get("risk_source", "").strip() or None
        risk.inherent_likelihood = request.form.get("inherent_likelihood", type=int)
        risk.inherent_impact = request.form.get("inherent_impact", type=int)
        risk.residual_likelihood = request.form.get("residual_likelihood", type=int)
        risk.residual_impact = request.form.get("residual_impact", type=int)
        risk.status = request.form.get("status", "Open")
        risk.treatment_type = request.form.get("treatment_type") or None
        risk.owner_id = request.form.get("owner_id", type=int) or None
        risk.due_date = _parse_date(request.form.get("due_date"))
        risk.review_frequency_days = request.form.get("review_frequency_days", type=int) or 90
        risk.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Risk updated.", "success")
        return redirect(url_for("risks.risk_detail", risk_id=risk.id))

    return render_template("risk/form.html", risk=risk, mode="edit", **ctx)


# ---------------------------------------------------------------------------
# Risk Detail
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/<int:risk_id>")
@login_required
def risk_detail(risk_id):
    """View a single risk with mitigations and review history."""
    risk = db.session.get(Risk, risk_id)
    if not risk:
        abort(404)
    ctx = _risk_context()
    mitigations = risk.mitigations.order_by(RiskMitigation.created_at.desc()).all()
    reviews = risk.reviews.order_by(RiskReview.review_date.desc()).all()
    return render_template(
        "risk/detail.html",
        risk=risk, mitigations=mitigations, reviews=reviews,
        today=date.today(),
        **ctx,
    )


# ---------------------------------------------------------------------------
# Add Mitigation
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/<int:risk_id>/mitigations", methods=["POST"])
@roles_required("admin", "auditor")
def add_mitigation(risk_id):
    """Add a mitigation/control to a risk."""
    risk = db.session.get(Risk, risk_id)
    if not risk:
        abort(404)
    mit = RiskMitigation(
        risk_id=risk.id,
        description=request.form.get("description", "").strip(),
        control_type=request.form.get("control_type") or None,
        status=request.form.get("mit_status", "Planned"),
        assigned_to_id=request.form.get("assigned_to_id", type=int) or None,
        due_date=_parse_date(request.form.get("due_date")),
    )
    db.session.add(mit)
    db.session.commit()
    flash("Mitigation added.", "success")
    return redirect(url_for("risks.risk_detail", risk_id=risk.id))


# ---------------------------------------------------------------------------
# Update Mitigation Status
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/mitigations/<int:mid>/status", methods=["POST"])
@roles_required("admin", "auditor")
def update_mitigation_status(mid):
    """Update a mitigation's status."""
    mit = db.session.get(RiskMitigation, mid)
    if not mit:
        abort(404)
    new_status = request.form.get("status", "Planned")
    mit.status = new_status
    if new_status == "Implemented" and not mit.completed_at:
        mit.completed_at = datetime.utcnow()
    db.session.commit()
    flash("Mitigation status updated.", "success")
    return redirect(url_for("risks.risk_detail", risk_id=mit.risk_id))


# ---------------------------------------------------------------------------
# Log Review
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/<int:risk_id>/review", methods=["POST"])
@roles_required("admin", "auditor")
def log_review(risk_id):
    """Log a periodic review for a risk."""
    risk = db.session.get(Risk, risk_id)
    if not risk:
        abort(404)
    prev_status = risk.status
    new_status = request.form.get("new_status", risk.status)
    notes = request.form.get("notes", "").strip()

    review = RiskReview(
        risk_id=risk.id,
        reviewed_by_id=g.current_user.id,
        notes=notes or None,
        previous_status=prev_status,
        new_status=new_status,
    )
    db.session.add(review)

    risk.status = new_status
    freq = risk.review_frequency_days or 90
    risk.next_review_date = date.today() + timedelta(days=freq)
    risk.updated_at = datetime.utcnow()
    db.session.commit()
    flash("Review logged. Next review scheduled.", "success")
    return redirect(url_for("risks.risk_detail", risk_id=risk.id))


# ---------------------------------------------------------------------------
# Delete Risk
# ---------------------------------------------------------------------------

@risks_bp.route("/risks/<int:risk_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_risk(risk_id):
    """Delete a risk and all related records."""
    risk = db.session.get(Risk, risk_id)
    if not risk:
        abort(404)
    db.session.delete(risk)
    db.session.commit()
    flash("Risk deleted.", "success")
    return redirect(url_for("risks.risk_register"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(val):
    """Parse a date string (YYYY-MM-DD) or return None."""
    if not val:
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None
