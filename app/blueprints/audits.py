"""Audit lifecycle management blueprint — CRUD, state machine, role-filtered listing.

Routes:
    GET  /audits              — List audits (filtered by role)
    GET  /audits/new          — New audit form
    POST /audits/new          — Create new audit
    GET  /audits/<id>         — Audit detail view
    POST /audits/<id>/review  — Transition to Review
    POST /audits/<id>/finalise — Transition to Completed
    POST /audits/<id>/archive — Transition to Archived
    GET  /audits/<id>/pdf     — Download PDF report
"""

import os
import uuid
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from app.extensions import db
from app.models.action import CorrectiveAction
from app.models.attachment import EvidenceAttachment
from app.models.audit import Audit, AuditScore, AuditSignOff, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User
from app.utils.rbac import has_role, login_required, roles_required
from app.utils.logging import log_activity

audits_bp = Blueprint("audits", __name__)


# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

VALID_TRANSITIONS = {
    "Draft": "In_Progress",
    "In_Progress": "Review",
    "Review": "Completed",
    "Completed": "Archived",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _can_modify_audit(audit: Audit) -> bool:
    """Return True if the audit is in a modifiable state (not Completed/Archived)."""
    return audit.status not in ("Completed", "Archived")


def _transition_audit(audit: Audit, target_status: str) -> tuple[bool, str]:
    """Attempt to transition *audit* to *target_status*.

    Returns (success, error_message).
    """
    expected_target = VALID_TRANSITIONS.get(audit.status)
    if expected_target is None or expected_target != target_status:
        return False, f"Cannot transition from {audit.status} to {target_status}"
    audit.status = target_status
    audit.updated_at = datetime.utcnow()
    return True, ""


def _calculate_overall_score(audit: Audit) -> float | None:
    """Calculate the overall average score excluding N/A and unscored criteria."""
    scores = audit.scores.filter(
        AuditScore.is_na == False,  # noqa: E712
        AuditScore.score.isnot(None),
    ).all()
    if not scores:
        return None
    return sum(s.score for s in scores) / len(scores)


def _build_sidebar_sections(audit: Audit) -> list[dict]:
    """Build sidebar navigation data for an audit's criteria.

    Returns a list of section dicts, each containing a list of criteria
    with their code, title, current score, N/A status, and URL.
    """
    sections = (
        TemplateSection.query
        .filter_by(template_id=audit.template_id)
        .order_by(TemplateSection.sort_order)
        .all()
    )

    # Build a lookup: criterion_id → AuditScore
    all_scores = audit.scores.all()
    score_by_criterion = {s.criterion_id: s for s in all_scores}

    sidebar = []
    for section in sections:
        criteria = section.criteria.order_by(TemplateCriterion.sort_order).all()
        if not criteria:
            continue

        items = []
        for criterion in criteria:
            audit_score_rec = score_by_criterion.get(criterion.id)
            score_val = None
            is_na = False
            if audit_score_rec:
                score_val = audit_score_rec.score
                is_na = audit_score_rec.is_na

            items.append({
                "code": criterion.code,
                "title": criterion.title,
                "score": score_val,
                "is_na": is_na,
                "url": url_for(
                    "audits.audit_score",
                    audit_id=audit.id,
                    code=criterion.code,
                ),
            })

        sidebar.append({
            "name": section.name,
            "criteria": items,
        })

    return sidebar


# ---------------------------------------------------------------------------
# Audit list — accessible to all authenticated users, filtered by role
# ---------------------------------------------------------------------------


@audits_bp.route("/audits")
@login_required
def audit_list():
    """Display all audits filtered by the current user's role."""
    user = g.current_user
    query = Audit.query

    if has_role(user, "admin") or has_role(user, "auditor"):
        # Admins and Auditors see all audits
        audits = query.order_by(Audit.created_at.desc()).all()
    elif has_role(user, "auditee"):
        # Auditees see only audits where they are the auditee
        audits = query.filter_by(auditee_id=user.id).order_by(
            Audit.created_at.desc()
        ).all()
    elif has_role(user, "viewer"):
        # Viewers see only Completed audits
        audits = query.filter_by(status="Completed").order_by(
            Audit.created_at.desc()
        ).all()
    else:
        audits = []

    return render_template("audit/list.html", audits=audits)


# ---------------------------------------------------------------------------
# Create new audit
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/new", methods=["GET", "POST"])
@roles_required("auditor")
def audit_new():
    """Create a new audit from an active template."""
    # Only active templates are available for new audits (Req 3.5)
    templates = AuditTemplate.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_active=True).all()

    if request.method == "POST":
        template_id = request.form.get("template_id", type=int)
        auditee_id = request.form.get("auditee_id", type=int) or None
        audit_date_str = request.form.get("audit_date", "").strip()
        assessment_period = request.form.get("assessment_period", "").strip()
        next_review_str = request.form.get("next_review_due", "").strip()

        # Validate template
        template = db.session.get(AuditTemplate, template_id)
        if template is None or not template.is_active:
            flash("Please select a valid active template.", "error")
            return render_template(
                "audit/new.html", templates=templates, users=users
            ), 400

        # Parse dates
        audit_date = None
        if audit_date_str:
            try:
                audit_date = date.fromisoformat(audit_date_str)
            except ValueError:
                flash("Invalid audit date format.", "error")
                return render_template(
                    "audit/new.html", templates=templates, users=users
                ), 400

        next_review_due = None
        if next_review_str:
            try:
                next_review_due = date.fromisoformat(next_review_str)
            except ValueError:
                flash("Invalid next review date format.", "error")
                return render_template(
                    "audit/new.html", templates=templates, users=users
                ), 400

        # Create the audit (Req 4.1)
        audit = Audit(
            template_id=template.id,
            auditor_id=g.current_user.id,
            auditee_id=auditee_id,
            status="Draft",
            audit_date=audit_date,
            assessment_period=assessment_period or None,
            next_review_due=next_review_due,
        )
        db.session.add(audit)
        db.session.flush()  # Get audit.id

        # Create AuditScore rows for all template criteria (unscored)
        sections = template.sections.order_by(TemplateSection.sort_order).all()
        for section in sections:
            criteria = section.criteria.order_by(TemplateCriterion.sort_order).all()
            for criterion in criteria:
                score = AuditScore(
                    audit_id=audit.id,
                    criterion_id=criterion.id,
                )
                db.session.add(score)
                db.session.flush()

                # Create EvidenceCheckState rows for each evidence item
                evidence_items = criterion.evidence_items.order_by(
                    CriterionEvidenceItem.sort_order
                ).all()
                for item in evidence_items:
                    check_state = EvidenceCheckState(
                        audit_score_id=score.id,
                        evidence_item_id=item.id,
                        is_checked=False,
                    )
                    db.session.add(check_state)

        db.session.commit()
        flash("Audit created successfully.", "success")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    return render_template("audit/new.html", templates=templates, users=users)


# ---------------------------------------------------------------------------
# Audit detail
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>")
@login_required
def audit_detail(audit_id):
    """Display audit detail / dashboard view with statistics.

    Calculates and passes to the template:
    - stats: total, completed, gap_count, partial_count, na_count, average_score
    - score_distribution: dict mapping score levels to counts
    - section_summary: list of dicts with section name, criteria count, avg score, gap count, first criterion code
    - compliance_trend: list of dicts with audit_date and overall_score for completed audits
    - upcoming_reminders: audits with next_review_due within 14 days
    """
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    user = g.current_user

    # Auditees can only see their own audits (Req 2.4)
    if (
        has_role(user, "auditee")
        and not has_role(user, "admin")
        and not has_role(user, "auditor")
        and audit.auditee_id != user.id
    ):
        abort(403)

    # Viewers can only see Completed audits (Req 2.5)
    if (
        has_role(user, "viewer")
        and not has_role(user, "admin")
        and not has_role(user, "auditor")
        and not has_role(user, "auditee")
        and audit.status != "Completed"
    ):
        abort(403)

    # ── Dashboard statistics (Req 6.1) ──
    all_scores = audit.scores.all()
    total_criteria = len(all_scores)

    scored_non_na = [s for s in all_scores if s.score is not None and not s.is_na]
    completed_count = len(scored_non_na)
    na_count = sum(1 for s in all_scores if s.is_na)
    gap_count = sum(1 for s in scored_non_na if s.score == 0)
    partial_count = sum(1 for s in scored_non_na if s.score in (1, 2))
    average_score = (
        sum(s.score for s in scored_non_na) / len(scored_non_na)
        if scored_non_na
        else None
    )

    stats = {
        "total": total_criteria,
        "completed": completed_count,
        "gap_count": gap_count,
        "partial_count": partial_count,
        "na_count": na_count,
        "average_score": average_score,
    }

    # ── Score distribution (Req 6.2) ──
    score_distribution = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for s in scored_non_na:
        if s.score in score_distribution:
            score_distribution[s.score] += 1

    # ── Section-by-section summary (Req 6.3, 6.5) ──
    sections = (
        TemplateSection.query
        .filter_by(template_id=audit.template_id)
        .order_by(TemplateSection.sort_order)
        .all()
    )

    # Build a lookup: criterion_id → AuditScore
    score_by_criterion = {s.criterion_id: s for s in all_scores}

    section_summary = []
    for section in sections:
        criteria = section.criteria.order_by(TemplateCriterion.sort_order).all()
        if not criteria:
            continue

        first_code = criteria[0].code
        section_scores = []
        section_gaps = 0

        for criterion in criteria:
            audit_score_rec = score_by_criterion.get(criterion.id)
            if audit_score_rec and audit_score_rec.score is not None and not audit_score_rec.is_na:
                section_scores.append(audit_score_rec.score)
                if audit_score_rec.score == 0:
                    section_gaps += 1

        section_avg = (
            sum(section_scores) / len(section_scores) if section_scores else None
        )

        section_summary.append({
            "name": section.name,
            "criteria_count": len(criteria),
            "average_score": section_avg,
            "gap_count": section_gaps,
            "first_code": first_code,
        })

    # ── Compliance trend (Req 6.4) ──
    completed_audits = (
        Audit.query
        .filter_by(status="Completed")
        .filter(Audit.overall_score.isnot(None))
        .filter(Audit.audit_date.isnot(None))
        .order_by(Audit.audit_date.asc())
        .all()
    )
    compliance_trend = [
        {
            "audit_date": a.audit_date.isoformat() if a.audit_date else None,
            "overall_score": a.overall_score,
        }
        for a in completed_audits
    ]

    # ── Upcoming reminders (Req 14.2, 14.4) ──
    today = date.today()
    reminder_cutoff = today + timedelta(days=14)
    upcoming_reminders = (
        Audit.query
        .filter(Audit.next_review_due.isnot(None))
        .filter(Audit.next_review_due >= today)
        .filter(Audit.next_review_due <= reminder_cutoff)
        .order_by(Audit.next_review_due.asc())
        .all()
    )

    return render_template(
        "audit/detail.html",
        audit=audit,
        stats=stats,
        score_distribution=score_distribution,
        section_summary=section_summary,
        compliance_trend=compliance_trend,
        upcoming_reminders=upcoming_reminders,
        sidebar_sections=_build_sidebar_sections(audit),
    )



# ---------------------------------------------------------------------------
# State transition routes
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/review", methods=["POST"])
@roles_required("auditor")
def audit_review(audit_id):
    """Transition audit from In_Progress to Review."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    success, error = _transition_audit(audit, "Review")
    if not success:
        return {"error": error}, 400

    log_activity("audit_status_change", {"audit_id": audit.id, "new_status": "Review"})
    db.session.commit()

    # Send email notification to auditee (Req 10.1)
    if audit.auditee_id:
        try:
            from app.services.mailer import send_email
            auditee = db.session.get(User, audit.auditee_id)
            if auditee and auditee.email:
                send_email(
                    to=auditee.email,
                    subject=f"Audit #{audit.id} submitted for your review",
                    body=(
                        f"Audit #{audit.id} has been submitted for review "
                        f"and requires your acknowledgement."
                    ),
                )
        except Exception:
            # Gracefully handle missing mailer service or SMTP not configured
            pass

    flash("Audit submitted for review.", "success")
    return redirect(url_for("audits.audit_detail", audit_id=audit.id))



@audits_bp.route("/audits/<int:audit_id>/finalise", methods=["POST"])
@roles_required("auditor")
def audit_finalise(audit_id):
    """Transition audit from Review to Completed."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    success, error = _transition_audit(audit, "Completed")
    if not success:
        return {"error": error}, 400

    # Record auditor finalisation timestamp in sign-off
    sign_off = audit.sign_off
    if sign_off is None:
        sign_off = AuditSignOff(audit_id=audit.id)
        db.session.add(sign_off)
    sign_off.auditor_finalised_at = datetime.utcnow()

    # Cache the overall score
    audit.overall_score = _calculate_overall_score(audit)

    log_activity("audit_status_change", {"audit_id": audit.id, "new_status": "Completed"})
    db.session.commit()
    flash("Audit finalised.", "success")
    return redirect(url_for("audits.audit_detail", audit_id=audit.id))


@audits_bp.route("/audits/<int:audit_id>/archive", methods=["POST"])
@roles_required("admin")
def audit_archive(audit_id):
    """Transition audit from Completed to Archived."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    success, error = _transition_audit(audit, "Archived")
    if not success:
        return {"error": error}, 400

    log_activity("audit_status_change", {"audit_id": audit.id, "new_status": "Archived"})
    db.session.commit()
    flash("Audit archived.", "success")
    return redirect(url_for("audits.audit_detail", audit_id=audit.id))


# ---------------------------------------------------------------------------
# PDF report download (Req 9.1–9.5)
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/pdf")
@roles_required("auditor", "admin")
def audit_pdf(audit_id):
    """Generate and return a downloadable PDF (or HTML fallback) report."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    from app.services.pdf import generate_audit_pdf

    content_bytes, content_type, filename = generate_audit_pdf(audit_id)

    return Response(
        content_bytes,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Criterion scoring form
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/score/<string:code>")
@roles_required("auditor")
def audit_score(audit_id, code):
    """Render the scoring form for a single criterion."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    # Find the criterion by code within the audit's template
    criterion = (
        TemplateCriterion.query
        .join(TemplateSection)
        .filter(
            TemplateSection.template_id == audit.template_id,
            TemplateCriterion.code == code,
        )
        .first()
    )
    if criterion is None:
        abort(404)

    # Load the AuditScore record for this criterion
    audit_score_record = AuditScore.query.filter_by(
        audit_id=audit.id,
        criterion_id=criterion.id,
    ).first()
    if audit_score_record is None:
        abort(404)

    # Load scoring anchors (0–4 descriptions)
    scoring_anchors = (
        CriterionScoringAnchor.query
        .filter_by(criterion_id=criterion.id)
        .order_by(CriterionScoringAnchor.score)
        .all()
    )

    # Load evidence items and their check states for this audit
    evidence_items = (
        CriterionEvidenceItem.query
        .filter_by(criterion_id=criterion.id)
        .order_by(CriterionEvidenceItem.sort_order)
        .all()
    )

    # Build a dict of evidence_item_id → is_checked
    evidence_states = {}
    for item in evidence_items:
        check_state = EvidenceCheckState.query.filter_by(
            audit_score_id=audit_score_record.id,
            evidence_item_id=item.id,
        ).first()
        evidence_states[item.id] = check_state.is_checked if check_state else False

    # Build prev/next navigation
    all_criteria = (
        TemplateCriterion.query
        .join(TemplateSection)
        .filter(TemplateSection.template_id == audit.template_id)
        .order_by(TemplateSection.sort_order, TemplateCriterion.sort_order)
        .all()
    )
    codes = [c.code for c in all_criteria]
    current_idx = codes.index(code) if code in codes else 0
    prev_code = codes[current_idx - 1] if current_idx > 0 else None
    next_code = codes[current_idx + 1] if current_idx < len(codes) - 1 else None

    # Load attachments for this criterion score (Req 8.3)
    attachments = audit_score_record.attachments.order_by(
        EvidenceAttachment.uploaded_at.desc()
    ).all()

    return render_template(
        "audit/score.html",
        audit=audit,
        criterion=criterion,
        audit_score=audit_score_record,
        scoring_anchors=scoring_anchors,
        evidence_items=evidence_items,
        evidence_states=evidence_states,
        prev_code=prev_code,
        next_code=next_code,
        attachments=attachments,
        sidebar_sections=_build_sidebar_sections(audit),
        current_criterion=code,
    )


# ---------------------------------------------------------------------------
# Gap checklist — criteria scored 0 (critical) or 1 (high)
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/gaps")
@login_required
def audit_gaps(audit_id):
    """Display gap checklist: criteria scored 0 or 1 with corrective actions."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    user = g.current_user

    # Auditees can only see their own audits
    if (
        has_role(user, "auditee")
        and not has_role(user, "admin")
        and not has_role(user, "auditor")
        and audit.auditee_id != user.id
    ):
        abort(403)

    # Viewers can only see Completed audits
    if (
        has_role(user, "viewer")
        and not has_role(user, "admin")
        and not has_role(user, "auditor")
        and not has_role(user, "auditee")
        and audit.status != "Completed"
    ):
        abort(403)

    # Query gap criteria: score 0 (critical) or 1 (high)
    gap_scores = (
        AuditScore.query
        .filter_by(audit_id=audit.id)
        .filter(AuditScore.score.in_([0, 1]))
        .join(TemplateCriterion, AuditScore.criterion_id == TemplateCriterion.id)
        .add_columns(
            TemplateCriterion.code,
            TemplateCriterion.title,
        )
        .all()
    )

    # Build gap items with priority and associated corrective actions
    gap_items = []
    for audit_score_obj, code, title in gap_scores:
        priority = "critical" if audit_score_obj.score == 0 else "high"
        actions = CorrectiveAction.query.filter_by(
            audit_id=audit.id, criterion_code=code
        ).all()
        gap_items.append({
            "code": code,
            "title": title,
            "score": audit_score_obj.score,
            "priority": priority,
            "actions": actions,
        })

    # Apply priority filter
    priority_filter = request.args.get("priority")
    if priority_filter in ("critical", "high"):
        gap_items = [g for g in gap_items if g["priority"] == priority_filter]

    # Apply status filter on corrective actions
    status_filter = request.args.get("status")
    if status_filter in ("Open", "In_Progress", "Completed", "Overdue"):
        gap_items = [
            g for g in gap_items
            if any(a.status == status_filter for a in g["actions"])
        ]

    # Calculate corrective action summary counts
    all_actions = CorrectiveAction.query.filter_by(audit_id=audit.id).all()
    summary = {
        "total": len(all_actions),
        "open": sum(1 for a in all_actions if a.status == "Open"),
        "in_progress": sum(1 for a in all_actions if a.status == "In_Progress"),
        "completed": sum(1 for a in all_actions if a.status == "Completed"),
        "overdue": sum(1 for a in all_actions if a.status == "Overdue"),
    }

    return render_template(
        "audit/gaps.html",
        audit=audit,
        gap_items=gap_items,
        summary=summary,
        priority_filter=priority_filter,
        status_filter=status_filter,
        sidebar_sections=_build_sidebar_sections(audit),
    )


# ---------------------------------------------------------------------------
# File upload for criterion evidence (Req 8.1, 8.2, 8.5)
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@audits_bp.route(
    "/audits/<int:audit_id>/score/<string:code>/upload", methods=["POST"]
)
@roles_required("auditor")
def upload_attachment(audit_id, code):
    """Upload a file attachment for a criterion score."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    # Reject uploads on Completed/Archived audits (Req 4.6)
    if audit.status in ("Completed", "Archived"):
        flash("This audit is locked and cannot be modified.", "error")
        return redirect(
            url_for("audits.audit_score", audit_id=audit.id, code=code)
        )

    # Find the criterion
    criterion = (
        TemplateCriterion.query.join(TemplateSection)
        .filter(
            TemplateSection.template_id == audit.template_id,
            TemplateCriterion.code == code,
        )
        .first()
    )
    if criterion is None:
        abort(404)

    # Find the AuditScore record
    audit_score_record = AuditScore.query.filter_by(
        audit_id=audit.id, criterion_id=criterion.id
    ).first()
    if audit_score_record is None:
        abort(404)

    # Validate file presence
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(
            url_for("audits.audit_score", audit_id=audit.id, code=code)
        )

    file = request.files["file"]
    if file.filename == "" or file.filename is None:
        flash("No file selected.", "error")
        return redirect(
            url_for("audits.audit_score", audit_id=audit.id, code=code)
        )

    # Validate file type (Req 8.2)
    if not _allowed_file(file.filename):
        flash(
            "File type not allowed. Accepted: PDF, PNG, JPG, JPEG, DOCX.",
            "error",
        )
        return redirect(
            url_for("audits.audit_score", audit_id=audit.id, code=code)
        )

    # Validate file size (Req 8.2) — read content to check size
    file_data = file.read()
    file_size = len(file_data)
    if file_size > MAX_FILE_SIZE:
        flash("File exceeds maximum size of 20 MB.", "error")
        return redirect(
            url_for("audits.audit_score", audit_id=audit.id, code=code)
        )

    # Generate unique filename and save (Req 8.1)
    original_filename = file.filename
    ext = original_filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, unique_filename)

    with open(filepath, "wb") as f:
        f.write(file_data)

    # Record metadata in database
    mime_type = MIME_TYPES.get(ext, "application/octet-stream")
    attachment = EvidenceAttachment(
        audit_score_id=audit_score_record.id,
        filename=unique_filename,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=mime_type,
        uploaded_by_id=g.current_user.id,
    )
    db.session.add(attachment)
    db.session.commit()

    flash("File uploaded successfully.", "success")
    return redirect(
        url_for("audits.audit_score", audit_id=audit.id, code=code)
    )


# ---------------------------------------------------------------------------
# File download (Req 8.3)
# ---------------------------------------------------------------------------


@audits_bp.route(
    "/audits/<int:audit_id>/score/<string:code>/download/<int:attachment_id>"
)
@login_required
def download_attachment(audit_id, code, attachment_id):
    """Serve an attachment file for download."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    attachment = db.session.get(EvidenceAttachment, attachment_id)
    if attachment is None:
        abort(404)

    # Verify the attachment belongs to this audit
    score_record = db.session.get(AuditScore, attachment.audit_score_id)
    if score_record is None or score_record.audit_id != audit.id:
        abort(404)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(
        upload_folder,
        attachment.filename,
        as_attachment=True,
        download_name=attachment.original_filename,
    )


# ---------------------------------------------------------------------------
# Auditee sign-off / acknowledgement (Req 10.2, 10.3, 10.4)
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/signoff", methods=["GET", "POST"])
@roles_required("auditee")
def audit_signoff(audit_id):
    """Auditee acknowledgement form — typed name and comments."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    user = g.current_user

    # Only the assigned auditee (or admin) can access sign-off
    if not has_role(user, "admin") and audit.auditee_id != user.id:
        abort(403)

    # Only available when audit is in Review or Completed status
    if audit.status not in ("Review", "Completed"):
        flash("Sign-off is only available for audits in Review or Completed status.", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    sign_off = audit.sign_off

    if request.method == "POST":
        typed_name = request.form.get("typed_name", "").strip()
        comments = request.form.get("comments", "").strip()

        if not typed_name:
            flash("Please enter your name to acknowledge.", "error")
            return render_template(
                "audit/signoff.html", audit=audit, sign_off=sign_off,
                sidebar_sections=_build_sidebar_sections(audit),
            ), 400

        # Create or update sign-off record
        if sign_off is None:
            sign_off = AuditSignOff(audit_id=audit.id)
            db.session.add(sign_off)

        sign_off.auditee_acknowledged_at = datetime.utcnow()
        sign_off.auditee_typed_name = typed_name
        sign_off.auditee_comments = comments or None
        db.session.commit()

        flash("Acknowledgement recorded successfully.", "success")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    return render_template(
        "audit/signoff.html", audit=audit, sign_off=sign_off,
        sidebar_sections=_build_sidebar_sections(audit),
    )


# ---------------------------------------------------------------------------
# Delete audit (admin/auditor only)
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/delete", methods=["POST"])
@roles_required("auditor", "admin")
def audit_delete(audit_id):
    """Delete an audit and all associated records."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    # Delete child records in correct order to respect FK constraints
    for score in audit.scores.all():
        # Delete evidence check states
        EvidenceCheckState.query.filter_by(audit_score_id=score.id).delete()
        # Delete attachments
        EvidenceAttachment.query.filter_by(audit_score_id=score.id).delete()

    # Delete all audit scores
    AuditScore.query.filter_by(audit_id=audit.id).delete()

    # Delete corrective actions
    CorrectiveAction.query.filter_by(audit_id=audit.id).delete()

    # Delete sign-off if exists
    if audit.sign_off:
        db.session.delete(audit.sign_off)

    # Delete the audit itself
    db.session.delete(audit)
    db.session.commit()

    log_activity("audit_deleted", {"audit_id": audit_id})
    flash("Audit deleted.", "success")
    return redirect(url_for("audits.audit_list"))


# ---------------------------------------------------------------------------
# Import JSON scores into an existing audit
# ---------------------------------------------------------------------------


@audits_bp.route("/audits/<int:audit_id>/import-scores", methods=["POST"])
@roles_required("auditor", "admin")
def audit_import_scores(audit_id):
    """Import scores from a legacy Tōtika JSON file into an existing audit."""
    import json

    audit = db.session.get(Audit, audit_id)
    if audit is None:
        abort(404)

    if not _can_modify_audit(audit):
        flash("This audit is locked and cannot be modified.", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".json"):
        flash("Only JSON files are accepted.", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    try:
        raw = json.loads(file.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        flash(f"Invalid JSON file: {exc}", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    scores_data = raw.get("scores", {})
    if not scores_data or not isinstance(scores_data, dict):
        flash("No scores found in JSON file.", "error")
        return redirect(url_for("audits.audit_detail", audit_id=audit.id))

    # Update meta fields if present
    meta = raw.get("meta", {})
    if isinstance(meta, dict):
        if meta.get("date"):
            try:
                audit.audit_date = date.fromisoformat(meta["date"])
            except (ValueError, TypeError):
                pass
        if meta.get("period"):
            audit.assessment_period = meta["period"]
        next_review = meta.get("nextReview") or meta.get("next")
        if next_review:
            try:
                audit.next_review_due = date.fromisoformat(next_review)
            except (ValueError, TypeError):
                pass

    # Build criterion code → TemplateCriterion lookup
    criteria = (
        TemplateCriterion.query.join(TemplateSection)
        .filter(TemplateSection.template_id == audit.template_id)
        .all()
    )
    criteria_by_code = {c.code: c for c in criteria}

    # Build evidence item lookup: criterion_id → sorted list
    all_evidence = CriterionEvidenceItem.query.filter(
        CriterionEvidenceItem.criterion_id.in_([c.id for c in criteria])
    ).order_by(CriterionEvidenceItem.sort_order).all()
    evidence_by_criterion: dict[int, list] = {}
    for ev in all_evidence:
        evidence_by_criterion.setdefault(ev.criterion_id, []).append(ev)

    updated = 0
    for code, score_entry in scores_data.items():
        if not isinstance(score_entry, dict):
            continue
        criterion = criteria_by_code.get(code)
        if criterion is None:
            continue

        audit_score = AuditScore.query.filter_by(
            audit_id=audit.id, criterion_id=criterion.id
        ).first()
        if audit_score is None:
            continue

        score_val = score_entry.get("score")
        if isinstance(score_val, int) and score_val in {0, 1, 2, 3, 4}:
            audit_score.score = score_val
        elif score_val is None:
            audit_score.score = None

        notes = score_entry.get("notes", "")
        if notes:
            audit_score.notes = notes

        na_reason = score_entry.get("naReason", "")
        if na_reason:
            audit_score.is_na = True
            audit_score.na_reason = na_reason

        # Evidence checks — array format or dict format
        ev_items = evidence_by_criterion.get(criterion.id, [])
        evidence_checked = score_entry.get("evidenceChecked")
        evidence_dict = score_entry.get("evidence")

        if isinstance(evidence_checked, list):
            for i, ev_item in enumerate(ev_items):
                if i < len(evidence_checked):
                    check_state = EvidenceCheckState.query.filter_by(
                        audit_score_id=audit_score.id,
                        evidence_item_id=ev_item.id,
                    ).first()
                    if check_state:
                        check_state.is_checked = bool(evidence_checked[i])
        elif isinstance(evidence_dict, dict):
            for ev_item in ev_items:
                val = evidence_dict.get(str(ev_item.id)) or evidence_dict.get(str(ev_item.sort_order))
                if val is not None:
                    check_state = EvidenceCheckState.query.filter_by(
                        audit_score_id=audit_score.id,
                        evidence_item_id=ev_item.id,
                    ).first()
                    if check_state:
                        check_state.is_checked = bool(val)

        updated += 1

    # Recalculate overall score
    scored = AuditScore.query.filter(
        AuditScore.audit_id == audit.id,
        AuditScore.is_na == False,  # noqa: E712
        AuditScore.score.isnot(None),
    ).all()
    if scored:
        audit.overall_score = sum(s.score for s in scored) / len(scored)

    if audit.status == "Draft":
        audit.status = "In_Progress"
        audit.updated_at = datetime.utcnow()

    db.session.commit()
    log_activity("import_scores", {"audit_id": audit.id, "source": file.filename, "criteria_updated": updated})
    flash(f"Imported scores for {updated} criteria from {file.filename}.", "success")
    return redirect(url_for("audits.audit_detail", audit_id=audit.id))


@audits_bp.route("/audits/import", methods=["POST"])
@roles_required("auditor", "admin")
def audit_import():
    """Import an audit from a legacy Tōtika JSON file."""
    import json

    from app.services.importer import import_legacy_json, validate_legacy_json

    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("audits.audit_list"))

    file = request.files["file"]
    if file.filename == "" or file.filename is None:
        flash("No file selected.", "error")
        return redirect(url_for("audits.audit_list"))

    if not file.filename.lower().endswith(".json"):
        flash("Only JSON files are accepted.", "error")
        return redirect(url_for("audits.audit_list"))

    try:
        data = json.loads(file.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        flash(f"Invalid JSON file: {exc}", "error")
        return redirect(url_for("audits.audit_list"))

    errors = validate_legacy_json(data)
    if errors:
        flash(f"Validation errors: {'; '.join(errors[:3])}", "error")
        return redirect(url_for("audits.audit_list"))

    try:
        audit = import_legacy_json(
            data,
            g.current_user.id,
            source_filename=file.filename,
            status="Completed",
        )
        log_activity("import", {"source": file.filename, "audit_id": audit.id})
        flash(f"Audit imported successfully (#{audit.id}).", "success")
    except ValueError as exc:
        flash(f"Import failed: {exc}", "error")
    except Exception as exc:
        flash(f"Import failed: {exc}", "error")

    return redirect(url_for("audits.audit_list"))
