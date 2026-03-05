"""JSON API blueprint — auto-save scoring, corrective actions, imports, attachments,
scoping, and compliance.

Routes:
    PUT    /api/audits/<id>/score        — Auto-save criterion score, evidence, notes
    POST   /api/audits/<id>/actions      — Create corrective action
    PUT    /api/audits/<id>/actions/<aid> — Update corrective action
    POST   /api/audits/<id>/import       — Import legacy JSON into existing audit
    DELETE /api/attachments/<id>         — Delete attachment
    GET    /api/audit/<id>/scoping       — Get scoping profile and applicability
    POST   /api/audit/<id>/scoping       — Submit scoping answers
    GET    /api/compliance/matrix        — Full compliance matrix JSON
    GET    /api/compliance/trend/<fw>    — Trend data for a framework
    GET    /api/compliance/breakdown/<id>— Control area breakdown for an audit
"""

import os
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import db
from app.models.action import CorrectiveAction
from app.models.attachment import EvidenceAttachment
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.scoping import CriterionApplicability, ScopingProfile, ScopingQuestion
from app.models.template import TemplateCriterion, TemplateSection
from app.services.scoping import evaluate_scoping, persist_scoping_profile, persist_applicability
from app.services.compliance import get_compliance_matrix, get_trend_data, get_control_area_breakdown
from app.utils.rbac import roles_required
from app.utils.logging import log_activity

api_bp = Blueprint("api", __name__)


def _calculate_overall_score(audit: Audit) -> float | None:
    """Calculate the overall average score excluding N/A, unscored, info-only, and not-applicable criteria."""
    from app.models.scoping import CriterionApplicability
    from app.models.template import TemplateCriterion, TemplateSection

    # Get not-applicable criterion IDs from scoping
    na_criteria = (
        CriterionApplicability.query
        .filter_by(audit_id=audit.id, applicability_status="not_applicable")
        .with_entities(CriterionApplicability.criterion_id)
        .all()
    )
    na_criterion_ids = {r[0] for r in na_criteria}

    # Get info-only criterion IDs
    info_only_ids = {
        c.id for c in TemplateCriterion.query
        .join(TemplateSection)
        .filter(TemplateSection.template_id == audit.template_id, TemplateCriterion.info_only == True)
        .all()
    }

    scores = (
        AuditScore.query
        .filter_by(audit_id=audit.id)
        .filter(
            AuditScore.is_na == False,  # noqa: E712
            AuditScore.score.isnot(None),
        )
        .all()
    )
    # Filter out not-applicable and info-only criteria
    applicable_scores = [s for s in scores if s.criterion_id not in na_criterion_ids and s.criterion_id not in info_only_ids]
    if not applicable_scores:
        return None
    return sum(s.score for s in applicable_scores) / len(applicable_scores)



@api_bp.route("/api/audits/<int:audit_id>/score", methods=["PUT"])
@roles_required("auditor")
def save_score(audit_id):
    """Auto-save endpoint: persist score, evidence checks, and notes."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    # Reject modifications on Completed/Archived audits (Req 4.6)
    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked and cannot be modified"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    criterion_code = data.get("criterion_code")
    if not criterion_code:
        return jsonify({"error": "criterion_code is required"}), 400

    # Find the criterion within the audit's template
    criterion = (
        TemplateCriterion.query
        .join(TemplateSection)
        .filter(
            TemplateSection.template_id == audit.template_id,
            TemplateCriterion.code == criterion_code,
        )
        .first()
    )
    if criterion is None:
        return jsonify({"error": f"Criterion '{criterion_code}' not found"}), 404

    # Find the AuditScore record
    audit_score = AuditScore.query.filter_by(
        audit_id=audit.id,
        criterion_id=criterion.id,
    ).first()
    if audit_score is None:
        return jsonify({"error": "Score record not found"}), 404

    # Extract fields from request
    score_value = data.get("score")  # 0-4 or None
    is_na = data.get("is_na", False)
    na_reason = data.get("na_reason", "")
    notes = data.get("notes", "")
    evidence_checks = data.get("evidence_checks", {})
    info_answer = data.get("info_answer", "")

    # Handle info-only criteria — skip score validation, save info_answer
    if criterion.info_only:
        audit_score.score = None
        audit_score.is_na = False
        audit_score.na_reason = None
        audit_score.info_answer = info_answer.strip() if info_answer else None
        audit_score.notes = notes if notes else None
        audit_score.updated_at = datetime.utcnow()

        # Persist evidence check states
        for item_id_str, is_checked in evidence_checks.items():
            try:
                item_id = int(item_id_str)
            except (ValueError, TypeError):
                continue
            check_state = EvidenceCheckState.query.filter_by(
                audit_score_id=audit_score.id,
                evidence_item_id=item_id,
            ).first()
            if check_state is not None:
                check_state.is_checked = bool(is_checked)

        # Auto-transition Draft → In_Progress on first save
        if audit.status == "Draft":
            audit.status = "In_Progress"
            audit.updated_at = datetime.utcnow()

        audit.overall_score = _calculate_overall_score(audit)
        audit.updated_at = datetime.utcnow()

        log_activity("score_change", {
            "audit_id": audit.id,
            "criterion_code": criterion_code,
            "info_only": True,
            "info_answer": audit_score.info_answer,
        })
        db.session.commit()

        return jsonify({
            "ok": True,
            "criterion_code": criterion_code,
            "score": None,
            "is_na": False,
            "info_only": True,
            "info_answer": audit_score.info_answer,
            "notes": audit_score.notes,
            "overall_score": audit.overall_score,
            "audit_status": audit.status,
        })

    # Validate N/A handling (Req 5.3)
    if is_na and not criterion.na_allowed:
        return jsonify({"error": f"N/A is not allowed for criterion '{criterion_code}'"}), 400

    if is_na and not na_reason.strip():
        return jsonify({"error": "A reason is required when marking a criterion as N/A"}), 400

    # Validate score value
    if score_value is not None:
        if not isinstance(score_value, int) or score_value < 0 or score_value > 4:
            return jsonify({"error": "Score must be an integer between 0 and 4"}), 400

    # Persist score data
    if is_na:
        audit_score.score = None
        audit_score.is_na = True
        audit_score.na_reason = na_reason.strip()
    else:
        audit_score.score = score_value
        audit_score.is_na = False
        audit_score.na_reason = None

    audit_score.notes = notes if notes else None
    audit_score.updated_at = datetime.utcnow()

    # Persist evidence check states
    for item_id_str, is_checked in evidence_checks.items():
        try:
            item_id = int(item_id_str)
        except (ValueError, TypeError):
            continue
        check_state = EvidenceCheckState.query.filter_by(
            audit_score_id=audit_score.id,
            evidence_item_id=item_id,
        ).first()
        if check_state is not None:
            check_state.is_checked = bool(is_checked)

    # Auto-transition Draft → In_Progress on first score save (Req 4.2)
    if audit.status == "Draft":
        audit.status = "In_Progress"
        audit.updated_at = datetime.utcnow()

    # Recalculate and cache overall score (Req 5.7)
    audit.overall_score = _calculate_overall_score(audit)
    audit.updated_at = datetime.utcnow()

    log_activity("score_change", {
        "audit_id": audit.id,
        "criterion_code": criterion_code,
        "score": audit_score.score,
        "is_na": audit_score.is_na,
    })
    db.session.commit()

    return jsonify({
        "ok": True,
        "criterion_code": criterion_code,
        "score": audit_score.score,
        "is_na": audit_score.is_na,
        "notes": audit_score.notes,
        "overall_score": audit.overall_score,
        "audit_status": audit.status,
    })


# ---------------------------------------------------------------------------
# Corrective action endpoints
# ---------------------------------------------------------------------------


@api_bp.route("/api/audits/<int:audit_id>/actions", methods=["POST"])
@roles_required("auditor")
def create_action(audit_id):
    """Create a corrective action for a gap item."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    # Reject on Completed/Archived audits
    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked and cannot be modified"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Validate required fields
    criterion_code = data.get("criterion_code", "").strip() if data.get("criterion_code") else ""
    description = data.get("description", "").strip() if data.get("description") else ""
    if not criterion_code:
        return jsonify({"error": "criterion_code is required"}), 400
    if not description:
        return jsonify({"error": "description is required"}), 400

    # Validate criterion exists in the audit's template
    criterion = (
        TemplateCriterion.query
        .join(TemplateSection)
        .filter(
            TemplateSection.template_id == audit.template_id,
            TemplateCriterion.code == criterion_code,
        )
        .first()
    )
    if criterion is None:
        return jsonify({"error": f"Criterion '{criterion_code}' not found"}), 404

    # Parse optional fields
    assigned_to_id = data.get("assigned_to_id")
    if assigned_to_id is not None:
        try:
            assigned_to_id = int(assigned_to_id)
        except (ValueError, TypeError):
            assigned_to_id = None

    due_date = None
    due_date_str = data.get("due_date", "")
    if due_date_str:
        try:
            from datetime import date
            due_date = date.fromisoformat(due_date_str)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD."}), 400

    priority = data.get("priority", "high")
    if priority not in ("critical", "high", "medium"):
        priority = "high"

    action = CorrectiveAction(
        audit_id=audit.id,
        criterion_code=criterion_code,
        description=description,
        assigned_to_id=assigned_to_id,
        priority=priority,
        status="Open",
        due_date=due_date,
    )
    db.session.add(action)
    db.session.commit()
    db.session.refresh(action)

    # Send email notification to assigned user (Req 7.7)
    if assigned_to_id:
        try:
            from app.services.mailer import send_email
            from app.models.user import User

            assigned_user = db.session.get(User, assigned_to_id)
            if assigned_user and assigned_user.email:
                send_email(
                    to=assigned_user.email,
                    subject=f"Corrective Action Assigned — {criterion_code}",
                    body=(
                        f"Hello {assigned_user.display_name},\n\n"
                        f"A corrective action has been assigned to you for "
                        f"criterion {criterion_code} on Audit #{audit.id}.\n\n"
                        f"Description: {description}\n"
                        f"Priority: {priority}\n"
                        f"Due date: {due_date.isoformat() if due_date else 'Not set'}\n\n"
                        f"Please address this action promptly.\n\n"
                        f"— Tōtika Audit Tool"
                    ),
                )
        except Exception:
            pass  # Gracefully skip if email fails

    return jsonify({
        "ok": True,
        "action": {
            "id": action.id,
            "audit_id": action.audit_id,
            "criterion_code": action.criterion_code,
            "description": action.description,
            "assigned_to_id": action.assigned_to_id,
            "priority": action.priority,
            "status": action.status,
            "due_date": action.due_date.isoformat() if action.due_date else None,
            "completed_at": None,
            "completed_by_id": None,
            "created_at": action.created_at.isoformat(),
        },
    }), 201


@api_bp.route("/api/audits/<int:audit_id>/actions/<int:action_id>", methods=["PUT"])
@roles_required("auditor")
def update_action(audit_id, action_id):
    """Update a corrective action's status or details."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    # Reject on Completed/Archived audits
    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked and cannot be modified"}), 400

    action = db.session.get(CorrectiveAction, action_id)
    if action is None or action.audit_id != audit.id:
        return jsonify({"error": "Corrective action not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Update fields if provided
    if "description" in data:
        desc = data["description"].strip() if data["description"] else ""
        if desc:
            action.description = desc

    if "assigned_to_id" in data:
        val = data["assigned_to_id"]
        if val is not None:
            try:
                action.assigned_to_id = int(val)
            except (ValueError, TypeError):
                pass
        else:
            action.assigned_to_id = None

    if "due_date" in data:
        due_str = data["due_date"]
        if due_str:
            try:
                from datetime import date
                action.due_date = date.fromisoformat(due_str)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD."}), 400
        else:
            action.due_date = None

    # Handle status change
    if "status" in data:
        new_status = data["status"]
        if new_status in ("Open", "In_Progress", "Completed", "Overdue"):
            old_status = action.status
            action.status = new_status

            # On completion: record completed_at and completed_by (Req 7.5)
            if new_status == "Completed" and old_status != "Completed":
                action.completed_at = datetime.utcnow()
                action.completed_by_id = g.current_user.id
            elif new_status != "Completed":
                # If moving away from Completed, clear completion fields
                action.completed_at = None
                action.completed_by_id = None

    if "notes" in data:
        action.notes = (data["notes"] or "").strip() or None

    if "resolution_notes" in data:
        action.resolution_notes = (data["resolution_notes"] or "").strip() or None

    if "priority" in data:
        p = data["priority"]
        if p in ("critical", "high", "medium"):
            action.priority = p

    db.session.commit()
    db.session.refresh(action)

    return jsonify({
        "ok": True,
        "action": {
            "id": action.id,
            "audit_id": action.audit_id,
            "criterion_code": action.criterion_code,
            "description": action.description,
            "assigned_to_id": action.assigned_to_id,
            "priority": action.priority,
            "status": action.status,
            "due_date": action.due_date.isoformat() if action.due_date else None,
            "completed_at": action.completed_at.isoformat() if action.completed_at else None,
            "completed_by_id": action.completed_by_id,
            "created_at": action.created_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# Attachment deletion (Req 8.4)
# ---------------------------------------------------------------------------


@api_bp.route("/api/attachments/<int:attachment_id>", methods=["DELETE"])
@roles_required("auditor")
def delete_attachment(attachment_id):
    """Delete an attachment — file from disk and record from database."""
    attachment = db.session.get(EvidenceAttachment, attachment_id)
    if attachment is None:
        return jsonify({"error": "Attachment not found"}), 404

    # Find the parent audit via the audit_score
    audit_score = db.session.get(AuditScore, attachment.audit_score_id)
    if audit_score is None:
        return jsonify({"error": "Attachment not found"}), 404

    audit = db.session.get(Audit, audit_score.audit_id)
    if audit is None:
        return jsonify({"error": "Attachment not found"}), 404

    # Reject deletion on Completed/Archived audits (Req 8.4)
    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked and cannot be modified"}), 400

    # Remove file from disk
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, attachment.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    # Remove database record
    db.session.delete(attachment)
    db.session.commit()

    return jsonify({"ok": True, "message": "Attachment deleted"})


# ---------------------------------------------------------------------------
# Action evidence upload / delete
# ---------------------------------------------------------------------------

EVIDENCE_MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "csv": "text/csv",
}

EVIDENCE_ALLOWED_EXTENSIONS = set(EVIDENCE_MIME_TYPES.keys())


@api_bp.route(
    "/api/audits/<int:audit_id>/actions/<int:action_id>/evidence",
    methods=["POST"],
)
@roles_required("auditor")
def upload_action_evidence(audit_id, action_id):
    """Upload evidence file for a corrective action."""
    import uuid

    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked"}), 400

    action = db.session.get(CorrectiveAction, action_id)
    if action is None or action.audit_id != audit.id:
        return jsonify({"error": "Action not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    original_filename = file.filename
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    if ext not in EVIDENCE_ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type .{ext} not allowed"}), 400

    file_data = file.read()
    file_size = len(file_data)
    if file_size == 0:
        return jsonify({"error": "Empty file"}), 400

    unique_filename = f"action_{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, unique_filename)
    with open(filepath, "wb") as f:
        f.write(file_data)

    from app.models.action import ActionEvidence

    evidence = ActionEvidence(
        action_id=action.id,
        filename=unique_filename,
        original_filename=original_filename,
        file_size=file_size,
        mime_type=EVIDENCE_MIME_TYPES.get(ext, "application/octet-stream"),
        uploaded_by_id=g.current_user.id,
    )
    db.session.add(evidence)
    db.session.commit()
    db.session.refresh(evidence)

    return jsonify({
        "ok": True,
        "evidence": {
            "id": evidence.id,
            "original_filename": evidence.original_filename,
            "file_size": evidence.file_size,
            "uploaded_at": evidence.uploaded_at.isoformat(),
        },
    }), 201


@api_bp.route("/api/action-evidence/<int:evidence_id>", methods=["DELETE"])
@roles_required("auditor")
def delete_action_evidence(evidence_id):
    """Delete an evidence file from a corrective action."""
    from app.models.action import ActionEvidence

    evidence = db.session.get(ActionEvidence, evidence_id)
    if evidence is None:
        return jsonify({"error": "Evidence not found"}), 404

    action = db.session.get(CorrectiveAction, evidence.action_id)
    if action is None:
        return jsonify({"error": "Evidence not found"}), 404

    audit = db.session.get(Audit, action.audit_id)
    if audit and audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, evidence.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(evidence)
    db.session.commit()

    return jsonify({"ok": True, "message": "Evidence deleted"})


# ---------------------------------------------------------------------------
# Legacy JSON import (Req 17.1, 17.2, 17.3, 17.8)
# ---------------------------------------------------------------------------


@api_bp.route("/api/audits/<int:audit_id>/import", methods=["POST"])
@roles_required("auditor", "admin")
def import_legacy(audit_id):
    """Import legacy JSON data into an existing audit.

    Expects a JSON body matching the legacy format.  The audit must be in
    Draft or In_Progress status.
    """
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    if audit.status in ("Completed", "Archived"):
        return jsonify({"error": "This audit is locked and cannot be modified"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    from app.services.importer import validate_legacy_json, import_legacy_json

    errors = validate_legacy_json(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        imported_audit = import_legacy_json(
            data,
            g.current_user.id,
            source_filename=f"api-import-audit-{audit_id}",
            status=audit.status,
        )
    except Exception as exc:
        return jsonify({"error": f"Import failed: {exc}"}), 500

    log_activity("import", {
        "audit_id": imported_audit.id,
        "source": "api",
        "type": "in-app",
    })
    db.session.commit()

    return jsonify({
        "ok": True,
        "audit_id": imported_audit.id,
        "message": "Legacy data imported successfully",
    }), 201


# ---------------------------------------------------------------------------
# Scoping API endpoints (Req 2.3, 2.4, 2.6, 2.7)
# ---------------------------------------------------------------------------


@api_bp.route("/api/audit/<int:audit_id>/scoping", methods=["GET"])
@roles_required("auditor")
def get_scoping(audit_id):
    """Return current scoping profile and applicability data."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    # Get scoping profile (answers)
    profiles = ScopingProfile.query.filter_by(audit_id=audit_id).all()
    answers = {}
    for p in profiles:
        q = db.session.get(ScopingQuestion, p.question_id)
        if q:
            answers[q.identifier] = p.answer_value

    # Get applicability
    app_records = CriterionApplicability.query.filter_by(audit_id=audit_id).all()
    applicability = {str(r.criterion_id): r.applicability_status for r in app_records}

    applicable_count = sum(1 for s in applicability.values() if s == "applicable")
    not_applicable_count = sum(1 for s in applicability.values() if s == "not_applicable")

    return jsonify({
        "ok": True,
        "audit_id": audit_id,
        "answers": answers,
        "applicability": applicability,
        "summary": {
            "total": len(applicability),
            "applicable": applicable_count,
            "not_applicable": not_applicable_count,
        },
    })


@api_bp.route("/api/audit/<int:audit_id>/scoping", methods=["POST"])
@roles_required("auditor")
def submit_scoping(audit_id):
    """Submit scoping answers, evaluate, and persist."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404

    if audit.status not in ("Draft", "In_Progress"):
        return jsonify({"error": "Scoping can only be modified for Draft or In Progress audits"}), 400

    data = request.get_json(silent=True)
    if data is None or "answers" not in data:
        return jsonify({"error": "JSON body with 'answers' dict required"}), 400

    answers = data["answers"]
    if not isinstance(answers, dict):
        return jsonify({"error": "'answers' must be a dict of identifier → answer"}), 400

    # Get old applicability for re-scoping
    old_app_records = CriterionApplicability.query.filter_by(audit_id=audit_id).all()
    old_app = {r.criterion_id: r.applicability_status for r in old_app_records}

    # Evaluate
    result = evaluate_scoping(audit_id, answers)
    new_app = result["criteria"]

    # Clear scores for newly applicable criteria
    if old_app:
        from app.services.scoping import clear_scores_for_newly_applicable
        clear_scores_for_newly_applicable(audit_id, old_app, new_app)

    # Persist
    persist_scoping_profile(audit_id, answers)
    persist_applicability(audit_id, new_app)

    return jsonify({
        "ok": True,
        "audit_id": audit_id,
        "applicable_count": result["applicable_count"],
        "not_applicable_count": result["not_applicable_count"],
        "total_count": result["total_count"],
    })


# ---------------------------------------------------------------------------
# Compliance API endpoints (Req 8.1, 9.2, 10.1)
# ---------------------------------------------------------------------------


@api_bp.route("/api/compliance/matrix")
@roles_required("auditor")
def compliance_matrix():
    """Return full compliance matrix JSON."""
    matrix = get_compliance_matrix()
    return jsonify({"ok": True, "matrix": matrix})


@api_bp.route("/api/compliance/trend/<string:framework>")
@roles_required("auditor")
def compliance_trend(framework):
    """Return trend data for a specific framework."""
    trend = get_trend_data(framework)
    return jsonify({"ok": True, "framework": framework, "trend": trend})


@api_bp.route("/api/compliance/breakdown/<int:audit_id>")
@roles_required("auditor")
def compliance_breakdown(audit_id):
    """Return control area breakdown for an audit."""
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return jsonify({"error": "Audit not found"}), 404
    breakdown = get_control_area_breakdown(audit_id)
    return jsonify({"ok": True, "audit_id": audit_id, "breakdown": breakdown})


# ---------------------------------------------------------------------------
# Passkey / WebAuthn endpoints
# ---------------------------------------------------------------------------

import base64
import json as _json
from datetime import datetime as _dt

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

from flask import session as flask_session
from app.models.user import User, UserPasskey
from app.utils.auth import create_session as create_user_session
from app.utils.proxy import get_client_ip
from app.utils.logging import log_activity


def _get_rp_id():
    """Return the Relying Party ID (domain) for WebAuthn."""
    return current_app.config.get("WEBAUTHN_RP_ID", "localhost")


def _get_rp_name():
    """Return the Relying Party name for WebAuthn."""
    return current_app.config.get("WEBAUTHN_RP_NAME", "Tōtika Audit Tool")


def _get_origin():
    """Return the expected origin for WebAuthn."""
    return current_app.config.get("WEBAUTHN_ORIGIN", "http://localhost:5000")


@api_bp.route("/api/passkey/register/begin", methods=["POST"])
@roles_required("admin")
def passkey_register_begin():
    """Start WebAuthn registration for the target user (admin action)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Existing credentials to exclude
    existing = UserPasskey.query.filter_by(user_id=user.id).all()
    exclude_creds = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
        for pk in existing
    ]

    options = generate_registration_options(
        rp_id=_get_rp_id(),
        rp_name=_get_rp_name(),
        user_id=str(user.id).encode("utf-8"),
        user_name=user.username,
        user_display_name=user.display_name,
        exclude_credentials=exclude_creds,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    # Store challenge in session for verification
    flask_session["webauthn_register_challenge"] = bytes_to_base64url(options.challenge)
    flask_session["webauthn_register_user_id"] = user.id

    return current_app.response_class(
        options_to_json(options), content_type="application/json"
    )


@api_bp.route("/api/passkey/register/complete", methods=["POST"])
@roles_required("admin")
def passkey_register_complete():
    """Complete WebAuthn registration."""
    challenge_b64 = flask_session.pop("webauthn_register_challenge", None)
    target_user_id = flask_session.pop("webauthn_register_user_id", None)

    if not challenge_b64 or not target_user_id:
        return jsonify({"error": "No registration in progress"}), 400

    user = db.session.get(User, target_user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    body = request.get_data()

    try:
        verification = verify_registration_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=_get_rp_id(),
            expected_origin=_get_origin(),
        )
    except Exception as exc:
        return jsonify({"error": f"Registration failed: {exc}"}), 400

    # Get passkey name from request or default
    try:
        req_data = _json.loads(body)
        passkey_name = req_data.get("name", "My Passkey")
    except Exception:
        passkey_name = "My Passkey"

    passkey = UserPasskey(
        user_id=user.id,
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        name=passkey_name,
        created_at=_dt.utcnow(),
    )
    db.session.add(passkey)
    db.session.commit()

    return jsonify({"ok": True, "passkey_id": passkey.id, "name": passkey.name})


@api_bp.route("/api/passkey/login/begin", methods=["POST"])
def passkey_login_begin():
    """Start WebAuthn authentication (no auth required — this IS the login)."""
    # Get all passkeys across all active users
    all_passkeys = (
        UserPasskey.query
        .join(User)
        .filter(User.is_active == True)  # noqa: E712
        .all()
    )

    allow_creds = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
        for pk in all_passkeys
    ]

    if not allow_creds:
        return jsonify({"error": "No passkeys registered"}), 404

    options = generate_authentication_options(
        rp_id=_get_rp_id(),
        allow_credentials=allow_creds,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    flask_session["webauthn_login_challenge"] = bytes_to_base64url(options.challenge)

    return current_app.response_class(
        options_to_json(options), content_type="application/json"
    )


@api_bp.route("/api/passkey/login/complete", methods=["POST"])
def passkey_login_complete():
    """Complete WebAuthn authentication and issue a session."""
    challenge_b64 = flask_session.pop("webauthn_login_challenge", None)
    if not challenge_b64:
        return jsonify({"error": "No login in progress"}), 400

    body = request.get_data()

    # Find the credential
    try:
        req_data = _json.loads(body)
    except Exception:
        return jsonify({"error": "Invalid request body"}), 400

    credential_id_b64 = req_data.get("rawId") or req_data.get("id")
    if not credential_id_b64:
        return jsonify({"error": "Missing credential ID"}), 400

    passkey = UserPasskey.query.filter_by(credential_id=credential_id_b64).first()
    if passkey is None:
        return jsonify({"error": "Unknown passkey"}), 401

    user = db.session.get(User, passkey.user_id)
    if user is None or not user.is_active:
        return jsonify({"error": "Account not available"}), 401

    try:
        verification = verify_authentication_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=_get_rp_id(),
            expected_origin=_get_origin(),
            credential_public_key=base64url_to_bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
        )
    except Exception as exc:
        return jsonify({"error": f"Verification failed: {exc}"}), 401

    # Update sign count
    passkey.sign_count = verification.new_sign_count
    db.session.commit()

    # Issue session — passkey login bypasses MFA
    ip = get_client_ip()
    token = create_user_session(user, ip=ip)
    log_activity("login", {"username": user.username, "method": "passkey"}, user_id=user.id, ip_address=ip)
    db.session.commit()

    from app.blueprints.auth import _set_session_cookie
    response_data = {"ok": True, "redirect": "/"}
    response = current_app.response_class(
        _json.dumps(response_data), content_type="application/json"
    )
    _set_session_cookie(response, token)
    return response


@api_bp.route("/api/passkey/<int:passkey_id>", methods=["DELETE"])
@roles_required("admin")
def delete_passkey(passkey_id):
    """Delete a passkey."""
    passkey = db.session.get(UserPasskey, passkey_id)
    if passkey is None:
        return jsonify({"error": "Passkey not found"}), 404

    db.session.delete(passkey)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/api/passkey/user/<int:user_id>", methods=["GET"])
@roles_required("admin")
def list_passkeys(user_id):
    """List all passkeys for a user."""
    passkeys = UserPasskey.query.filter_by(user_id=user_id).all()
    return jsonify({
        "passkeys": [
            {
                "id": pk.id,
                "name": pk.name,
                "created_at": pk.created_at.isoformat(),
            }
            for pk in passkeys
        ]
    })
