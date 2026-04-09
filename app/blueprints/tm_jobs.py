"""Traffic Management Job Site Risk blueprint.

Routes:
    GET  /tm/jobs                              — Job site list
    GET  /tm/jobs/new                          — Create job form
    POST /tm/jobs                              — Create job
    GET  /tm/jobs/<id>                         — Job dashboard
    GET  /tm/jobs/<id>/subjects                — Subject selection
    POST /tm/jobs/<id>/subjects                — Save subjects & populate risks
    GET  /tm/jobs/<id>/risks                   — Risk tracking
    GET  /tm/jobs/<id>/risks/<rid>             — Edit risk
    POST /tm/jobs/<id>/risks/<rid>             — Save risk edits
    POST /tm/jobs/<id>/risks/<rid>/controls/<cid>/toggle — Toggle control
    POST /tm/jobs/<id>/risks/add               — Add custom risk
    GET  /tm/jobs/<id>/report                  — Printable report
"""

from datetime import datetime, date

from flask import (
    Blueprint, abort, flash, g, jsonify, redirect,
    render_template, request, url_for,
)

from app.extensions import db
from app.models.tm_risk import (
    TMRiskSubject, TMRiskTemplate, TMRiskTemplateControl,
    TMJobSite, TMJobSiteSubject, TMJobSiteRisk, TMJobSiteRiskControl,
    JOB_STATUSES, SITE_RISK_STATUSES, HIERARCHY_ORDER,
    LIKELIHOOD_LABELS, SEVERITY_LABELS,
    calc_risk_level, risk_level_colour,
)
from app.utils.rbac import login_required, roles_required

tm_bp = Blueprint("tm_jobs", __name__)


def _parse_date(val):
    if not val:
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _tm_context():
    return dict(
        job_statuses=JOB_STATUSES,
        risk_statuses=SITE_RISK_STATUSES,
        hierarchy_order=HIERARCHY_ORDER,
        likelihood_labels=LIKELIHOOD_LABELS,
        severity_labels=SEVERITY_LABELS,
        calc_risk_level=calc_risk_level,
        risk_level_colour=risk_level_colour,
    )


# ---------------------------------------------------------------------------
# Job Site List
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs")
@login_required
def job_list():
    jobs = TMJobSite.query.order_by(TMJobSite.created_at.desc()).all()
    return render_template("tm/job_list.html", jobs=jobs, **_tm_context())


# ---------------------------------------------------------------------------
# Create Job Site
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/new", methods=["GET"])
@roles_required("admin", "auditor")
def job_new():
    return render_template("tm/job_form.html", job=None, mode="create", **_tm_context())


@tm_bp.route("/tm/jobs", methods=["POST"])
@roles_required("admin", "auditor")
def job_create():
    job = TMJobSite(
        job_number=request.form.get("job_number", "").strip() or None,
        site_name=request.form.get("site_name", "").strip(),
        address=request.form.get("address", "").strip() or None,
        suburb=request.form.get("suburb", "").strip() or None,
        city=request.form.get("city", "").strip() or None,
        client_name=request.form.get("client_name", "").strip() or None,
        rca_name=request.form.get("rca_name", "").strip() or None,
        start_date=_parse_date(request.form.get("start_date")),
        end_date=_parse_date(request.form.get("end_date")),
        speed_limit_kmh=request.form.get("speed_limit_kmh", type=int),
        work_zone_speed_kmh=request.form.get("work_zone_speed_kmh", type=int),
        stms_name=request.form.get("stms_name", "").strip() or None,
        created_by=g.current_user.id,
    )
    db.session.add(job)
    db.session.commit()
    flash("Job site created. Now select which risk subjects apply.", "success")
    return redirect(url_for("tm_jobs.job_subjects", job_id=job.id))


# ---------------------------------------------------------------------------
# Job Dashboard
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>")
@login_required
def job_detail(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)
    risks = job.risks.filter(TMJobSiteRisk.status != "NA").all()
    critical = sum(1 for r in risks if calc_risk_level(r.inherent_score) == "Critical")
    high = sum(1 for r in risks if calc_risk_level(r.inherent_score) == "High")
    medium = sum(1 for r in risks if calc_risk_level(r.inherent_score) == "Medium")
    low = sum(1 for r in risks if calc_risk_level(r.inherent_score) == "Low")
    selected_subjects = [s.subject for s in job.subjects.all()]
    return render_template(
        "tm/job_dashboard.html", job=job, risks=risks,
        selected_subjects=selected_subjects,
        critical=critical, high=high, medium=medium, low=low,
        **_tm_context(),
    )


# ---------------------------------------------------------------------------
# Subject Selection
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/subjects", methods=["GET"])
@login_required
def job_subjects(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)
    subjects = TMRiskSubject.query.filter_by(is_active=True).order_by(TMRiskSubject.sort_order).all()
    selected_ids = {s.subject_id for s in job.subjects.all()}
    return render_template(
        "tm/subject_select.html", job=job, subjects=subjects,
        selected_ids=selected_ids, **_tm_context(),
    )


@tm_bp.route("/tm/jobs/<int:job_id>/subjects", methods=["POST"])
@roles_required("admin", "auditor")
def job_subjects_save(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)

    import logging
    logger = logging.getLogger(__name__)

    raw_ids = request.form.getlist("subject_ids")
    logger.warning("Subject form data: subject_ids=%s, all_keys=%s", raw_ids, list(request.form.keys()))

    if not raw_ids:
        flash("No subjects selected.", "error")
        return redirect(url_for("tm_jobs.job_subjects", job_id=job.id))

    selected_ids = set(map(int, raw_ids))
    existing_ids = {s.subject_id for s in job.subjects.all()}

    # Add new subjects and populate risks
    for sid in selected_ids - existing_ids:
        jss = TMJobSiteSubject(
            job_site_id=job.id, subject_id=sid, added_by=g.current_user.id,
        )
        db.session.add(jss)

        # Copy template risks for this subject
        templates = TMRiskTemplate.query.filter_by(subject_id=sid, is_active=True).order_by(TMRiskTemplate.sort_order).all()
        for tmpl in templates:
            jr = TMJobSiteRisk(
                job_site_id=job.id,
                subject_id=sid,
                template_id=tmpl.id,
                title=tmpl.title,
                description=tmpl.description,
                likelihood=tmpl.likelihood,
                severity=tmpl.severity,
                risk_level=calc_risk_level(tmpl.likelihood * tmpl.severity),
                causes=tmpl.causes,
                consequences=tmpl.consequences,
                legislation=tmpl.legislation,
                emergency_action=tmpl.emergency_action,
                copttm_ref=tmpl.copttm_ref,
                sort_order=tmpl.sort_order,
            )
            db.session.add(jr)
            db.session.flush()

            # Copy template controls
            for tc in tmpl.controls.all():
                db.session.add(TMJobSiteRiskControl(
                    job_site_risk_id=jr.id,
                    template_control_id=tc.id,
                    hierarchy=tc.hierarchy,
                    control=tc.control,
                    sort_order=tc.sort_order,
                ))

    # Mark removed subjects' risks as NA (don't delete user-edited data)
    for sid in existing_ids - selected_ids:
        TMJobSiteSubject.query.filter_by(job_site_id=job.id, subject_id=sid).delete()
        for risk in TMJobSiteRisk.query.filter_by(job_site_id=job.id, subject_id=sid).all():
            risk.status = "NA"

    # Activate job if it was Draft and subjects are selected
    if job.status == "Draft" and selected_ids:
        job.status = "Active"

    db.session.commit()
    flash("Risk subjects updated. Risks have been populated.", "success")
    return redirect(url_for("tm_jobs.job_risks", job_id=job.id))


# ---------------------------------------------------------------------------
# Risk Tracking
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/risks")
@login_required
def job_risks(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)

    risks = job.risks.order_by(TMJobSiteRisk.subject_id, TMJobSiteRisk.sort_order).all()

    # Group by subject
    grouped = {}
    for r in risks:
        if r.subject_id not in grouped:
            grouped[r.subject_id] = {"subject": r.subject, "risks": []}
        grouped[r.subject_id]["risks"].append(r)

    # Sort groups by subject sort_order
    groups = sorted(grouped.values(), key=lambda g: g["subject"].sort_order)

    # Summary
    active_risks = [r for r in risks if r.status != "NA"]
    critical = sum(1 for r in active_risks if calc_risk_level(r.inherent_score) == "Critical")
    high = sum(1 for r in active_risks if calc_risk_level(r.inherent_score) == "High")
    medium = sum(1 for r in active_risks if calc_risk_level(r.inherent_score) == "Medium")
    low = sum(1 for r in active_risks if calc_risk_level(r.inherent_score) == "Low")

    subjects = TMRiskSubject.query.filter_by(is_active=True).order_by(TMRiskSubject.sort_order).all()

    return render_template(
        "tm/risk_tracking.html", job=job, groups=groups,
        total=len(active_risks), critical=critical, high=high, medium=medium, low=low,
        subjects=subjects, **_tm_context(),
    )


# ---------------------------------------------------------------------------
# Edit Risk
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/risks/<int:risk_id>", methods=["GET"])
@login_required
def risk_edit(job_id, risk_id):
    job = db.session.get(TMJobSite, job_id)
    risk = db.session.get(TMJobSiteRisk, risk_id)
    if not job or not risk or risk.job_site_id != job.id:
        abort(404)
    subjects = TMRiskSubject.query.filter_by(is_active=True).order_by(TMRiskSubject.sort_order).all()
    return render_template(
        "tm/risk_edit.html", job=job, risk=risk, subjects=subjects, **_tm_context(),
    )


@tm_bp.route("/tm/jobs/<int:job_id>/risks/<int:risk_id>", methods=["POST"])
@roles_required("admin", "auditor")
def risk_save(job_id, risk_id):
    job = db.session.get(TMJobSite, job_id)
    risk = db.session.get(TMJobSiteRisk, risk_id)
    if not job or not risk or risk.job_site_id != job.id:
        abort(404)

    risk.title = request.form.get("title", "").strip()
    risk.description = request.form.get("description", "").strip() or None
    risk.likelihood = request.form.get("likelihood", type=int) or risk.likelihood
    risk.severity = request.form.get("severity", type=int) or risk.severity
    risk.risk_level = calc_risk_level(risk.likelihood * risk.severity)
    risk.residual_likelihood = request.form.get("residual_likelihood", type=int)
    risk.residual_severity = request.form.get("residual_severity", type=int)
    if risk.residual_likelihood and risk.residual_severity:
        risk.residual_risk_level = calc_risk_level(risk.residual_likelihood * risk.residual_severity)
    risk.emergency_action = request.form.get("emergency_action", "").strip() or None
    risk.copttm_ref = request.form.get("copttm_ref", "").strip() or None
    risk.status = request.form.get("status", risk.status)
    risk.notes = request.form.get("notes", "").strip() or None
    risk.updated_at = datetime.utcnow()

    # Update causes/consequences from textarea (one per line)
    causes_raw = request.form.get("causes", "").strip()
    risk.causes = [c.strip() for c in causes_raw.split("\n") if c.strip()] if causes_raw else []
    consequences_raw = request.form.get("consequences", "").strip()
    risk.consequences = [c.strip() for c in consequences_raw.split("\n") if c.strip()] if consequences_raw else []

    db.session.commit()
    flash("Risk updated.", "success")
    return redirect(url_for("tm_jobs.job_risks", job_id=job.id))


# ---------------------------------------------------------------------------
# Toggle Control (AJAX)
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/risks/<int:risk_id>/controls/<int:control_id>/toggle", methods=["POST"])
@login_required
def toggle_control(job_id, risk_id, control_id):
    ctrl = db.session.get(TMJobSiteRiskControl, control_id)
    if not ctrl or ctrl.risk.job_site_id != job_id or ctrl.job_site_risk_id != risk_id:
        return jsonify({"error": "Not found"}), 404

    ctrl.is_implemented = not ctrl.is_implemented
    if ctrl.is_implemented:
        ctrl.implemented_by = g.current_user.display_name
        ctrl.implemented_at = datetime.utcnow()
    else:
        ctrl.implemented_by = None
        ctrl.implemented_at = None
    db.session.commit()

    job = db.session.get(TMJobSite, job_id)
    return jsonify({
        "implemented": ctrl.is_implemented,
        "job_completion_pct": job.control_completion_pct,
    })


# ---------------------------------------------------------------------------
# Add Custom Risk
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/risks/add", methods=["POST"])
@roles_required("admin", "auditor")
def risk_add(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)

    subject_id = request.form.get("subject_id", type=int)
    if not subject_id:
        flash("Please select a risk subject.", "error")
        return redirect(url_for("tm_jobs.job_risks", job_id=job.id))

    likelihood = request.form.get("likelihood", type=int) or 3
    severity = request.form.get("severity", type=int) or 3

    risk = TMJobSiteRisk(
        job_site_id=job.id,
        subject_id=subject_id,
        template_id=None,
        title=request.form.get("title", "").strip() or "New Risk",
        description=request.form.get("description", "").strip() or None,
        likelihood=likelihood,
        severity=severity,
        risk_level=calc_risk_level(likelihood * severity),
    )
    db.session.add(risk)
    db.session.commit()
    flash("Custom risk added.", "success")
    return redirect(url_for("tm_jobs.risk_edit", job_id=job.id, risk_id=risk.id))


# ---------------------------------------------------------------------------
# Printable Report
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/jobs/<int:job_id>/report")
@login_required
def job_report(job_id):
    job = db.session.get(TMJobSite, job_id)
    if not job:
        abort(404)

    risks = job.risks.order_by(TMJobSiteRisk.subject_id, TMJobSiteRisk.sort_order).all()
    grouped = {}
    for r in risks:
        if r.status == "NA":
            continue
        if r.subject_id not in grouped:
            grouped[r.subject_id] = {"subject": r.subject, "risks": []}
        grouped[r.subject_id]["risks"].append(r)
    groups = sorted(grouped.values(), key=lambda g: g["subject"].sort_order)

    return render_template(
        "tm/report.html", job=job, groups=groups, **_tm_context(),
    )


# ---------------------------------------------------------------------------
# Admin: Manage Risk Subjects & Templates
# ---------------------------------------------------------------------------

@tm_bp.route("/tm/admin/subjects")
@roles_required("admin")
def admin_subjects():
    subjects = TMRiskSubject.query.order_by(TMRiskSubject.sort_order).all()
    return render_template("tm/admin_subjects.html", subjects=subjects, **_tm_context())


@tm_bp.route("/tm/admin/subjects/add", methods=["POST"])
@roles_required("admin")
def admin_subject_add():
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    if not code or not name:
        flash("Code and name are required.", "error")
        return redirect(url_for("tm_jobs.admin_subjects"))

    existing = TMRiskSubject.query.filter_by(code=code).first()
    if existing:
        flash(f"Subject code '{code}' already exists.", "error")
        return redirect(url_for("tm_jobs.admin_subjects"))

    max_order = db.session.query(db.func.max(TMRiskSubject.sort_order)).scalar() or 0
    subj = TMRiskSubject(
        code=code,
        name=name,
        icon=request.form.get("icon", "").strip() or "📋",
        description=request.form.get("description", "").strip() or None,
        sort_order=max_order + 1,
    )
    db.session.add(subj)
    db.session.commit()
    flash(f"Subject '{name}' created.", "success")
    return redirect(url_for("tm_jobs.admin_subjects"))


@tm_bp.route("/tm/admin/subjects/<int:subject_id>/edit", methods=["POST"])
@roles_required("admin")
def admin_subject_edit(subject_id):
    subj = db.session.get(TMRiskSubject, subject_id)
    if not subj:
        abort(404)
    subj.name = request.form.get("name", "").strip() or subj.name
    subj.icon = request.form.get("icon", "").strip() or subj.icon
    subj.description = request.form.get("description", "").strip() or None
    subj.is_active = request.form.get("is_active") == "1"
    db.session.commit()
    flash(f"Subject '{subj.name}' updated.", "success")
    return redirect(url_for("tm_jobs.admin_subjects"))


@tm_bp.route("/tm/admin/subjects/<int:subject_id>/delete", methods=["POST"])
@roles_required("admin")
def admin_subject_delete(subject_id):
    subj = db.session.get(TMRiskSubject, subject_id)
    if not subj:
        abort(404)
    # Check if any job sites use this subject
    used = TMJobSiteRisk.query.filter_by(subject_id=subject_id).first()
    if used:
        flash(f"Cannot delete '{subj.name}' — it's used in job site risks. Deactivate it instead.", "error")
        return redirect(url_for("tm_jobs.admin_subjects"))
    db.session.delete(subj)
    db.session.commit()
    flash(f"Subject '{subj.name}' deleted.", "success")
    return redirect(url_for("tm_jobs.admin_subjects"))


@tm_bp.route("/tm/admin/subjects/<int:subject_id>/templates/add", methods=["POST"])
@roles_required("admin")
def admin_template_add(subject_id):
    subj = db.session.get(TMRiskSubject, subject_id)
    if not subj:
        abort(404)

    code = request.form.get("code", "").strip().upper()
    title = request.form.get("title", "").strip()
    if not code or not title:
        flash("Code and title are required.", "error")
        return redirect(url_for("tm_jobs.admin_subjects"))

    existing = TMRiskTemplate.query.filter_by(code=code).first()
    if existing:
        flash(f"Template code '{code}' already exists.", "error")
        return redirect(url_for("tm_jobs.admin_subjects"))

    likelihood = request.form.get("likelihood", type=int) or 3
    severity = request.form.get("severity", type=int) or 3
    max_order = db.session.query(db.func.max(TMRiskTemplate.sort_order)).filter(
        TMRiskTemplate.subject_id == subject_id
    ).scalar() or 0

    tmpl = TMRiskTemplate(
        subject_id=subject_id,
        code=code,
        title=title,
        description=request.form.get("description", "").strip() or None,
        likelihood=likelihood,
        severity=severity,
        risk_level=calc_risk_level(likelihood * severity),
        sort_order=max_order + 1,
    )
    db.session.add(tmpl)
    db.session.commit()
    flash(f"Template risk '{title}' added to {subj.name}.", "success")
    return redirect(url_for("tm_jobs.admin_subjects"))


@tm_bp.route("/tm/admin/templates/<int:template_id>/delete", methods=["POST"])
@roles_required("admin")
def admin_template_delete(template_id):
    tmpl = db.session.get(TMRiskTemplate, template_id)
    if not tmpl:
        abort(404)
    name = tmpl.title
    db.session.delete(tmpl)
    db.session.commit()
    flash(f"Template risk '{name}' deleted.", "success")
    return redirect(url_for("tm_jobs.admin_subjects"))
