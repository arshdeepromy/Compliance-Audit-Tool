"""Legacy JSON import/export service.

Provides validation, import, and export of audit data in the legacy
single-file Tōtika audit tool JSON format.

Legacy format::

    {
      "meta": {
        "assessor": "string",
        "auditee": "string",
        "date": "YYYY-MM-DD",
        "period": "string",
        "nextReview": "YYYY-MM-DD"
      },
      "scores": {
        "MB1": { "score": 0-4 or null, "notes": "string",
                 "evidence": {"item_id": true/false} },
        ...
      },
      "gapItems": [
        {
          "criterion_code": "MB1",
          "description": "string",
          "priority": "critical|high|medium",
          "status": "Open|In_Progress|Completed|Overdue",
          "due_date": "YYYY-MM-DD",
          "assigned_to": "string"
        }
      ]
    }
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.extensions import db
from app.models.action import CorrectiveAction
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    TemplateCriterion,
    TemplateSection,
)

logger = logging.getLogger(__name__)

VALID_SCORES = {0, 1, 2, 3, 4}
VALID_PRIORITIES = {"critical", "high", "medium"}
VALID_ACTION_STATUSES = {"Open", "In_Progress", "Completed", "Overdue"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_legacy_json(data: dict) -> list[str]:
    """Validate a legacy JSON structure and return a list of errors.

    An empty list means the data is valid and can be imported.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Data must be a JSON object"]

    # --- meta ---
    meta = data.get("meta")
    if meta is None:
        errors.append("Missing required field: meta")
    elif not isinstance(meta, dict):
        errors.append("Field 'meta' must be an object")
    else:
        if not meta.get("date"):
            errors.append("Missing required field: meta.date")
        else:
            try:
                date.fromisoformat(meta["date"])
            except (ValueError, TypeError):
                errors.append("Invalid date format for meta.date: expected YYYY-MM-DD")

        if meta.get("nextReview"):
            try:
                date.fromisoformat(meta["nextReview"])
            except (ValueError, TypeError):
                errors.append("Invalid date format for meta.nextReview: expected YYYY-MM-DD")
        elif meta.get("next"):
            try:
                date.fromisoformat(meta["next"])
            except (ValueError, TypeError):
                errors.append("Invalid date format for meta.next: expected YYYY-MM-DD")

    # --- scores ---
    scores = data.get("scores")
    if scores is None:
        errors.append("Missing required field: scores")
    elif not isinstance(scores, dict):
        errors.append("Field 'scores' must be an object")
    else:
        for code, score_data in scores.items():
            if not isinstance(score_data, dict):
                errors.append(f"Score entry for '{code}' must be an object")
                continue
            score_val = score_data.get("score")
            if score_val is not None:
                if not isinstance(score_val, int) or score_val not in VALID_SCORES:
                    errors.append(
                        f"Invalid score for {code}: must be 0–4 or null"
                    )

    # --- gapItems (optional) ---
    gap_items = data.get("gapItems")
    if gap_items is not None:
        if not isinstance(gap_items, list):
            errors.append("Field 'gapItems' must be an array")
        else:
            for i, item in enumerate(gap_items):
                if not isinstance(item, dict):
                    errors.append(f"gapItems[{i}] must be an object")
                    continue
                # Accept either legacy "criterion_code" or rich "criteria" list
                has_code = bool(item.get("criterion_code"))
                has_criteria = isinstance(item.get("criteria"), list) and len(item.get("criteria", [])) > 0
                if not has_code and not has_criteria:
                    errors.append(f"gapItems[{i}]: missing criterion_code or criteria")
                # Accept either "description" or "title"/"action"
                has_desc = bool(item.get("description"))
                has_title = bool(item.get("title"))
                has_action = bool(item.get("action"))
                if not has_desc and not has_title and not has_action:
                    errors.append(f"gapItems[{i}]: missing description (or title/action)")
                if item.get("priority"):
                    norm_pri = item["priority"].lower() if isinstance(item["priority"], str) else ""
                    if norm_pri not in VALID_PRIORITIES:
                        errors.append(
                            f"gapItems[{i}]: invalid priority '{item['priority']}'"
                        )
                if item.get("status"):
                    norm_st = item["status"].lower() if isinstance(item["status"], str) else ""
                    valid_lower = {s.lower() for s in VALID_ACTION_STATUSES}
                    if norm_st not in valid_lower:
                        errors.append(
                            f"gapItems[{i}]: invalid status '{item['status']}'"
                        )
                if item.get("due_date"):
                    try:
                        date.fromisoformat(item["due_date"])
                    except (ValueError, TypeError):
                        errors.append(
                            f"gapItems[{i}]: invalid due_date format"
                        )

    return errors


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def _find_builtin_template() -> AuditTemplate | None:
    """Return the built-in Tōtika template, or None."""
    return AuditTemplate.query.filter_by(is_builtin=True, is_active=True).first()


def import_legacy_json(
    data: dict,
    user_id: int,
    *,
    source_filename: str | None = None,
    status: str = "Completed",
) -> Audit:
    """Create an Audit with AuditScore and CorrectiveAction records from legacy JSON.

    Parameters
    ----------
    data:
        Validated legacy JSON dict (call ``validate_legacy_json`` first).
    user_id:
        The user performing the import (used as auditor_id).
    source_filename:
        Optional filename to record in ``Audit.imported_from``.
    status:
        Audit status to set. Defaults to ``"Completed"`` for seed imports.

    Returns
    -------
    Audit
        The newly created audit record (already committed).
    """
    template = _find_builtin_template()
    if template is None:
        raise ValueError("No active built-in template found for import")

    meta = data.get("meta", {})
    scores_data = data.get("scores", {})
    gap_items = data.get("gapItems", [])

    # Parse dates
    audit_date = None
    if meta.get("date"):
        try:
            audit_date = date.fromisoformat(meta["date"])
        except (ValueError, TypeError):
            pass

    next_review = None
    next_review_raw = meta.get("nextReview") or meta.get("next")
    if next_review_raw:
        try:
            next_review = date.fromisoformat(next_review_raw)
        except (ValueError, TypeError):
            pass

    # Create audit record
    audit = Audit(
        template_id=template.id,
        auditor_id=user_id,
        status=status,
        audit_date=audit_date,
        assessment_period=meta.get("period", ""),
        next_review_due=next_review,
        imported_from=source_filename,
    )
    db.session.add(audit)
    db.session.flush()  # get audit.id

    # Build a lookup: criterion code → TemplateCriterion
    criteria = (
        TemplateCriterion.query.join(TemplateSection)
        .filter(TemplateSection.template_id == template.id)
        .all()
    )
    criteria_by_code: dict[str, TemplateCriterion] = {c.code: c for c in criteria}

    # Build evidence item lookup: criterion_id → list[CriterionEvidenceItem]
    all_evidence = CriterionEvidenceItem.query.filter(
        CriterionEvidenceItem.criterion_id.in_([c.id for c in criteria])
    ).all()
    evidence_by_criterion: dict[int, list[CriterionEvidenceItem]] = {}
    for ev in all_evidence:
        evidence_by_criterion.setdefault(ev.criterion_id, []).append(ev)

    # Create AuditScore records for every criterion in the template
    scored_values: list[int] = []
    for code, criterion in criteria_by_code.items():
        score_entry = scores_data.get(code, {})
        score_val = score_entry.get("score") if isinstance(score_entry, dict) else None
        notes = score_entry.get("notes", "") if isinstance(score_entry, dict) else ""
        evidence_checks = (
            score_entry.get("evidence", {}) if isinstance(score_entry, dict) else {}
        )
        # Also support "evidenceChecked" array format: [true, false, true, ...]
        evidence_checked_arr = (
            score_entry.get("evidenceChecked") if isinstance(score_entry, dict) else None
        )

        is_na = False
        na_reason = None
        if score_val is not None and isinstance(score_val, int) and score_val in VALID_SCORES:
            scored_values.append(score_val)
        elif score_val is None and isinstance(score_entry, dict) and "score" in score_entry:
            # Explicitly null score — could be N/A or unscored
            pass

        audit_score = AuditScore(
            audit_id=audit.id,
            criterion_id=criterion.id,
            score=score_val if (isinstance(score_val, int) and score_val in VALID_SCORES) else None,
            is_na=is_na,
            na_reason=na_reason,
            notes=notes if notes else None,
        )
        db.session.add(audit_score)
        db.session.flush()  # get audit_score.id

        # Create EvidenceCheckState records
        ev_items = evidence_by_criterion.get(criterion.id, [])
        # Sort by sort_order so array-based evidenceChecked aligns correctly
        ev_items_sorted = sorted(ev_items, key=lambda e: e.sort_order)
        for idx, ev_item in enumerate(ev_items_sorted):
            is_checked = False
            # Try array format first (evidenceChecked: [true, false, ...])
            if isinstance(evidence_checked_arr, list) and idx < len(evidence_checked_arr):
                is_checked = bool(evidence_checked_arr[idx])
            elif isinstance(evidence_checks, dict):
                # Legacy format uses string item IDs or evidence item text keys
                # Try matching by evidence_item.id (as string) first
                checked_val = evidence_checks.get(str(ev_item.id))
                if checked_val is None:
                    # Also try matching by sort_order-based key
                    checked_val = evidence_checks.get(str(ev_item.sort_order))
                if checked_val is not None:
                    is_checked = bool(checked_val)

            db.session.add(
                EvidenceCheckState(
                    audit_score_id=audit_score.id,
                    evidence_item_id=ev_item.id,
                    is_checked=is_checked,
                )
            )

    # Calculate overall score
    if scored_values:
        audit.overall_score = sum(scored_values) / len(scored_values)

    # Create CorrectiveAction records from gapItems
    # Supports both legacy format (criterion_code, description) and
    # rich format (criteria[], title, action, UPPER-CASE priority/status).
    if gap_items and isinstance(gap_items, list):
        for item in gap_items:
            if not isinstance(item, dict):
                continue

            # Resolve criterion codes: rich format uses "criteria" (list),
            # legacy uses "criterion_code" (string).
            criterion_codes: list[str] = []
            if item.get("criteria") and isinstance(item["criteria"], list):
                criterion_codes = [c for c in item["criteria"] if isinstance(c, str)]
            elif item.get("criterion_code"):
                criterion_codes = [item["criterion_code"]]

            if not criterion_codes:
                continue

            # Resolve description: rich format has title + action,
            # legacy has description.
            description = item.get("description", "")
            if not description:
                parts = []
                if item.get("title"):
                    parts.append(item["title"])
                if item.get("action"):
                    parts.append(item["action"])
                description = " — ".join(parts) if parts else ""
            if not description:
                continue

            # Normalise priority (CRITICAL → critical, HIGH → high, etc.)
            raw_priority = item.get("priority", "high")
            priority = raw_priority.lower() if isinstance(raw_priority, str) else "high"
            if priority not in VALID_PRIORITIES:
                priority = "high"

            # Normalise status (OPEN → Open, IN_PROGRESS → In_Progress, etc.)
            raw_status = item.get("status", "Open")
            status_map = {
                "open": "Open",
                "in_progress": "In_Progress",
                "completed": "Completed",
                "overdue": "Overdue",
            }
            norm_status = status_map.get(
                raw_status.lower() if isinstance(raw_status, str) else "",
                "Open",
            )

            due_date_val = None
            if item.get("due_date"):
                try:
                    due_date_val = date.fromisoformat(item["due_date"])
                except (ValueError, TypeError):
                    pass

            # Extract rich fields from gap item
            gap_item_id = item.get("id", "")          # e.g. "G001"
            title_text = item.get("title", "")
            action_text = item.get("action", "")
            form_or_doc = item.get("formOrDoc", "")
            quantity_val = item.get("quantity", "")
            max_age_val = item.get("maxAge", "")
            max_age_months_val = item.get("maxAgeMonths")
            signed_val = item.get("signed")
            signed_by_val = item.get("signedBy", "")
            category_val = item.get("category", "")
            criteria_codes_str = ",".join(criterion_codes)

            # Create one CorrectiveAction per criterion code so the gaps
            # page can look them up by code.
            for code in criterion_codes:
                if code not in criteria_by_code:
                    continue  # skip unknown codes
                action = CorrectiveAction(
                    audit_id=audit.id,
                    criterion_code=code,
                    description=description,
                    priority=priority,
                    status=norm_status,
                    due_date=due_date_val,
                    gap_item_id=gap_item_id or None,
                    title=title_text or None,
                    action_text=action_text or None,
                    form_or_doc=form_or_doc or None,
                    quantity=quantity_val or None,
                    max_age=max_age_val or None,
                    max_age_months=max_age_months_val if isinstance(max_age_months_val, int) else None,
                    signed=signed_val if isinstance(signed_val, bool) else None,
                    signed_by=signed_by_val or None,
                    category=category_val or None,
                    criteria_codes=criteria_codes_str or None,
                )
                db.session.add(action)

    db.session.commit()
    db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_to_legacy_json(audit_id: int) -> dict:
    """Export an audit back to the legacy JSON format.

    Returns a dict matching the legacy structure for round-trip validation.
    """
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        raise ValueError(f"Audit {audit_id} not found")

    # Build meta
    meta: dict[str, Any] = {
        "assessor": "",
        "auditee": "",
        "date": audit.audit_date.isoformat() if audit.audit_date else "",
        "period": audit.assessment_period or "",
        "nextReview": audit.next_review_due.isoformat() if audit.next_review_due else "",
    }

    # Populate assessor/auditee names from user records
    if audit.auditor_id:
        from app.models.user import User

        auditor = db.session.get(User, audit.auditor_id)
        if auditor:
            meta["assessor"] = auditor.display_name
    if audit.auditee_id:
        from app.models.user import User

        auditee_user = db.session.get(User, audit.auditee_id)
        if auditee_user:
            meta["auditee"] = auditee_user.display_name

    # Build scores
    scores_dict: dict[str, dict] = {}
    audit_scores = AuditScore.query.filter_by(audit_id=audit.id).all()
    for ascore in audit_scores:
        criterion = db.session.get(TemplateCriterion, ascore.criterion_id)
        if criterion is None:
            continue

        # Build evidence checks
        evidence: dict[str, bool] = {}
        check_states = EvidenceCheckState.query.filter_by(
            audit_score_id=ascore.id
        ).all()
        for cs in check_states:
            evidence[str(cs.evidence_item_id)] = cs.is_checked

        scores_dict[criterion.code] = {
            "score": ascore.score,
            "notes": ascore.notes or "",
            "evidence": evidence,
        }

    # Build gapItems
    gap_items: list[dict] = []
    actions = CorrectiveAction.query.filter_by(audit_id=audit.id).all()
    for action in actions:
        gap_item = {
            "criterion_code": action.criterion_code,
            "description": action.description,
            "priority": action.priority,
            "status": action.status,
            "due_date": action.due_date.isoformat() if action.due_date else "",
            "assigned_to": "",
        }
        if action.gap_item_id:
            gap_item["id"] = action.gap_item_id
        if action.title:
            gap_item["title"] = action.title
        if action.action_text:
            gap_item["action"] = action.action_text
        if action.form_or_doc:
            gap_item["formOrDoc"] = action.form_or_doc
        if action.quantity:
            gap_item["quantity"] = action.quantity
        if action.max_age:
            gap_item["maxAge"] = action.max_age
        if action.max_age_months is not None:
            gap_item["maxAgeMonths"] = action.max_age_months
        if action.signed is not None:
            gap_item["signed"] = action.signed
        if action.signed_by:
            gap_item["signedBy"] = action.signed_by
        if action.category:
            gap_item["category"] = action.category
        if action.criteria_codes:
            gap_item["criteria"] = action.criteria_codes.split(",")
        gap_items.append(gap_item)

    return {
        "meta": meta,
        "scores": scores_dict,
        "gapItems": gap_items,
    }


# ---------------------------------------------------------------------------
# Seed data loading
# ---------------------------------------------------------------------------


def load_seed_data(app) -> None:
    """Scan the seed_data directory for JSON files and import them.

    Tracks imported files in SeedFileTracker to prevent duplicates on restart.
    Logs each import to the activity log.
    """
    import json
    import os

    from app.models.log import SeedFileTracker
    from app.utils.logging import log_activity

    seed_dir = app.config.get("SEED_DATA_DIR", "seed_data")
    if not os.path.isdir(seed_dir):
        logger.info("Seed data directory '%s' not found — skipping.", seed_dir)
        return

    json_files = sorted(
        f for f in os.listdir(seed_dir) if f.lower().endswith(".json")
    )
    if not json_files:
        logger.info("No JSON files found in seed data directory.")
        return

    # Find the default admin user to use as the importer
    from app.models.user import User

    admin_user = User.query.filter_by(username="admin").first()
    if admin_user is None:
        logger.warning("No admin user found — cannot import seed data.")
        return

    for filename in json_files:
        # Check if already imported
        existing = SeedFileTracker.query.filter_by(filename=filename).first()
        if existing is not None:
            logger.info("Seed file '%s' already imported — skipping.", filename)
            continue

        filepath = os.path.join(seed_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read seed file '%s': %s", filename, exc)
            continue

        # Validate
        errors = validate_legacy_json(data)
        if errors:
            logger.warning(
                "Seed file '%s' has validation errors: %s", filename, errors
            )
            continue

        # Import as Completed audit
        try:
            audit = import_legacy_json(
                data,
                admin_user.id,
                source_filename=filename,
                status="Completed",
            )
        except Exception as exc:
            logger.warning("Failed to import seed file '%s': %s", filename, exc)
            continue

        # Track the import
        tracker = SeedFileTracker(
            filename=filename,
            imported_at=datetime.utcnow(),
            audit_id=audit.id,
        )
        db.session.add(tracker)

        # Log to activity log
        log_activity(
            "import",
            {"source": filename, "audit_id": audit.id, "type": "seed"},
            user_id=admin_user.id,
        )
        db.session.commit()

        logger.info(
            "Imported seed file '%s' as audit id=%d.", filename, audit.id
        )
