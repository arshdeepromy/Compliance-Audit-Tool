"""Template management blueprint — admin-only CRUD for audit templates.

Routes:
    GET  /admin/templates           — list all templates
    GET  /admin/templates/new       — new template form
    POST /admin/templates/new       — create template
    GET  /admin/templates/<id>      — edit template form
    POST /admin/templates/<id>      — update template (versioning if audits exist)
    POST /admin/templates/<id>/toggle — activate / deactivate
"""

import json
from datetime import datetime

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.scoping import ScopingQuestion, ScopingRule
from app.utils.rbac import roles_required

templates_bp = Blueprint("templates", __name__)


@templates_bp.before_request
def _set_admin_page():
    """Mark templates pages as admin/templates for the admin nav."""
    g.admin_page = "templates"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sections_from_form(form):
    """Parse section/criterion data from the submitted form.

    Returns a list of dicts:
    [
        {
            "name": str,
            "criteria": [
                {
                    "code": str, "title": str, "guidance": str,
                    "question": str, "na_allowed": bool, "tip": str,
                    "scoring": [{"score": int, "description": str}, ...],
                    "evidence": [{"text": str, "is_required": bool}, ...],
                },
                ...
            ],
        },
        ...
    ]
    """
    sections = []
    section_idx = 0

    while True:
        section_name = form.get(f"section_{section_idx}_name")
        if section_name is None:
            break

        section_name = section_name.strip()
        if not section_name:
            section_idx += 1
            continue

        criteria = []
        crit_idx = 0
        while True:
            code = form.get(f"section_{section_idx}_criterion_{crit_idx}_code")
            if code is None:
                break

            code = code.strip()
            title = (
                form.get(f"section_{section_idx}_criterion_{crit_idx}_title", "")
                .strip()
            )
            if not code or not title:
                crit_idx += 1
                continue

            guidance = (
                form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_guidance", ""
                ).strip()
                or None
            )
            question = (
                form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_question", ""
                ).strip()
                or None
            )
            na_allowed = (
                form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_na_allowed"
                )
                == "on"
            )
            tip = (
                form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_tip", ""
                ).strip()
                or None
            )

            # Scoring anchors (0–4)
            scoring = []
            for score_val in range(5):
                desc = form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_score_{score_val}",
                    "",
                ).strip()
                if desc:
                    scoring.append({"score": score_val, "description": desc})

            # Evidence items
            evidence = []
            ev_idx = 0
            while True:
                ev_text = form.get(
                    f"section_{section_idx}_criterion_{crit_idx}_evidence_{ev_idx}_text"
                )
                if ev_text is None:
                    break
                ev_text = ev_text.strip()
                if ev_text:
                    ev_required = (
                        form.get(
                            f"section_{section_idx}_criterion_{crit_idx}_evidence_{ev_idx}_required"
                        )
                        == "on"
                    )
                    evidence.append({"text": ev_text, "is_required": ev_required})
                ev_idx += 1

            criteria.append(
                {
                    "code": code,
                    "title": title,
                    "guidance": guidance,
                    "question": question,
                    "na_allowed": na_allowed,
                    "tip": tip,
                    "scoring": scoring,
                    "evidence": evidence,
                }
            )
            crit_idx += 1

        sections.append({"name": section_name, "criteria": criteria})
        section_idx += 1

    return sections


def _build_template_from_sections(template, sections_data):
    """Populate a template with sections, criteria, anchors, and evidence items.

    Assumes the template has already been added to the session and flushed
    (so ``template.id`` is available).
    """
    criterion_sort = 0
    for section_order, section_data in enumerate(sections_data):
        section = TemplateSection(
            template_id=template.id,
            name=section_data["name"],
            sort_order=section_order,
        )
        db.session.add(section)
        db.session.flush()

        for crit_data in section_data["criteria"]:
            criterion_sort += 1
            criterion = TemplateCriterion(
                section_id=section.id,
                code=crit_data["code"],
                title=crit_data["title"],
                guidance=crit_data.get("guidance"),
                question=crit_data.get("question"),
                na_allowed=crit_data.get("na_allowed", False),
                tip=crit_data.get("tip"),
                sort_order=criterion_sort,
            )
            db.session.add(criterion)
            db.session.flush()

            for anchor in crit_data.get("scoring", []):
                db.session.add(
                    CriterionScoringAnchor(
                        criterion_id=criterion.id,
                        score=anchor["score"],
                        description=anchor["description"],
                    )
                )

            for ev_order, ev in enumerate(crit_data.get("evidence", [])):
                db.session.add(
                    CriterionEvidenceItem(
                        criterion_id=criterion.id,
                        text=ev["text"],
                        is_required=ev.get("is_required", False),
                        sort_order=ev_order,
                    )
                )


def _template_has_audits(template_id):
    """Return True if any audits reference this template."""
    from app.models.audit import Audit

    return (
        db.session.query(Audit.id)
        .filter_by(template_id=template_id)
        .first()
        is not None
    )


def _parse_scoping_from_form(form):
    """Parse scoping question hidden fields from the submitted form.

    Returns a list of dicts with question data and nested rules.
    """
    questions = []
    q_idx = 0
    while True:
        prefix = f"scoping_question_{q_idx}_"
        identifier = form.get(f"{prefix}identifier", "").strip()
        if not identifier:
            break
        text = form.get(f"{prefix}text", "").strip()
        answer_type = form.get(f"{prefix}answer_type", "yes_no").strip()
        options_str = form.get(f"{prefix}options", "").strip()
        options = [o.strip() for o in options_str.split(",") if o.strip()] if options_str else []

        rules = []
        r_idx = 0
        while True:
            r_prefix = f"{prefix}rule_{r_idx}_"
            trigger = form.get(f"{r_prefix}trigger", "").strip()
            if not trigger:
                break
            rules.append({
                "trigger_answer": trigger,
                "target_type": form.get(f"{r_prefix}target_type", "criterion").strip(),
                "target_code": form.get(f"{r_prefix}target_code", "").strip(),
                "applicability_status": form.get(f"{r_prefix}status", "not_applicable").strip(),
            })
            r_idx += 1

        questions.append({
            "identifier": identifier,
            "question_text": text,
            "answer_type": answer_type,
            "options_json": json.dumps(options) if options else None,
            "sort_order": q_idx,
            "rules": rules,
        })
        q_idx += 1
    return questions


def _build_scoping_questions(template, scoping_data, valid_codes):
    """Create ScopingQuestion and ScopingRule records.

    Args:
        template: The AuditTemplate (must have id set).
        scoping_data: List of question dicts from ``_parse_scoping_from_form``.
        valid_codes: Dict with ``criteria`` (set of codes) and ``sections`` (set of names).

    Returns:
        List of validation error strings (empty if all valid).
    """
    errors = []
    for q_data in scoping_data:
        question = ScopingQuestion(
            template_id=template.id,
            identifier=q_data["identifier"],
            question_text=q_data["question_text"],
            answer_type=q_data["answer_type"],
            options_json=q_data["options_json"],
            sort_order=q_data["sort_order"],
        )
        db.session.add(question)
        db.session.flush()

        for rule_data in q_data["rules"]:
            target_code = rule_data["target_code"]
            if not target_code:
                continue
            # Validate target_code exists
            if rule_data["target_type"] == "criterion" and target_code not in valid_codes["criteria"]:
                errors.append(
                    f"Rule for question '{q_data['identifier']}': criterion code '{target_code}' not found in template"
                )
                continue
            if rule_data["target_type"] == "section" and target_code not in valid_codes["sections"]:
                errors.append(
                    f"Rule for question '{q_data['identifier']}': section '{target_code}' not found in template"
                )
                continue

            rule = ScopingRule(
                question_id=question.id,
                trigger_answer=rule_data["trigger_answer"],
                target_type=rule_data["target_type"],
                target_code=target_code,
                applicability_status=rule_data["applicability_status"],
            )
            db.session.add(rule)
    return errors


def _increment_version(version_str):
    """Increment a version string, e.g. '1.0' → '2.0', '3' → '4'."""
    parts = version_str.split(".")
    try:
        parts[0] = str(int(parts[0]) + 1)
    except (ValueError, IndexError):
        return version_str + ".1"
    return ".".join(parts)


def _valid_codes_from_sections(sections_data):
    """Build a dict of valid criteria codes and section names from parsed sections data."""
    criteria_codes = set()
    section_names = set()
    for sec in sections_data:
        section_names.add(sec["name"])
        for crit in sec.get("criteria", []):
            criteria_codes.add(crit["code"])
    return {"criteria": criteria_codes, "sections": section_names}


def _save_scoping_questions(template, form, sections_data):
    """Parse scoping questions from form and save them, returning any validation errors."""
    scoping_data = _parse_scoping_from_form(form)
    if not scoping_data:
        return []
    valid_codes = _valid_codes_from_sections(sections_data)
    errors = _build_scoping_questions(template, scoping_data, valid_codes)
    return errors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@templates_bp.route("/admin/templates")
@roles_required("admin")
def template_list():
    """Display all audit templates."""
    all_templates = AuditTemplate.query.order_by(
        AuditTemplate.is_active.desc(), AuditTemplate.created_at.desc()
    ).all()
    return render_template("admin/templates_list.html", templates=all_templates)


@templates_bp.route("/admin/templates/new", methods=["GET", "POST"])
@roles_required("admin")
def template_new():
    """Create a new custom audit template."""
    if request.method == "GET":
        return render_template("admin/template_form.html", template=None)

    # --- POST: create template ---
    name = request.form.get("name", "").strip()
    version = request.form.get("version", "1.0").strip()
    description = request.form.get("description", "").strip() or None
    domain_type = request.form.get("domain_type", "").strip() or None
    compliance_framework = request.form.get("compliance_framework", "").strip() or None

    if not name:
        flash("Template name is required.", "error")
        return render_template("admin/template_form.html", template=None), 400

    sections_data = _parse_sections_from_form(request.form)

    template = AuditTemplate(
        name=name,
        version=version,
        description=description,
        is_active=True,
        is_builtin=False,
        domain_type=domain_type,
        compliance_framework=compliance_framework,
    )
    db.session.add(template)
    db.session.flush()

    _build_template_from_sections(template, sections_data)

    # Parse and save scoping questions
    scoping_errors = _save_scoping_questions(template, request.form, sections_data)
    if scoping_errors:
        for err in scoping_errors:
            flash(err, "error")

    db.session.commit()

    flash(f"Template '{name}' created.", "success")
    return redirect(url_for("templates.template_list"))


@templates_bp.route("/admin/templates/<int:template_id>", methods=["GET", "POST"])
@roles_required("admin")
def template_edit(template_id):
    """Edit an existing audit template.

    If the template has existing audits, a new version is created so that
    those audits continue to reference the original snapshot (Req 3.3).
    """
    template = db.session.get(AuditTemplate, template_id)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("templates.template_list"))

    if request.method == "GET":
        return render_template("admin/template_form.html", template=template)

    # --- POST: update template ---
    name = request.form.get("name", "").strip()
    version = request.form.get("version", "").strip()
    description = request.form.get("description", "").strip() or None
    domain_type = request.form.get("domain_type", "").strip() or None
    compliance_framework = request.form.get("compliance_framework", "").strip() or None

    if not name:
        flash("Template name is required.", "error")
        return (
            render_template("admin/template_form.html", template=template),
            400,
        )

    sections_data = _parse_sections_from_form(request.form)

    if _template_has_audits(template_id):
        # --- Versioning: create a new template version ---
        new_version = version or _increment_version(template.version)

        new_template = AuditTemplate(
            name=name,
            version=new_version,
            description=description,
            is_active=True,
            is_builtin=template.is_builtin,
            domain_type=domain_type,
            compliance_framework=compliance_framework,
        )
        db.session.add(new_template)
        db.session.flush()

        _build_template_from_sections(new_template, sections_data)

        # Parse and save scoping questions for the new version
        scoping_errors = _save_scoping_questions(new_template, request.form, sections_data)
        if scoping_errors:
            for err in scoping_errors:
                flash(err, "error")

        # Deactivate the old version so auditors use the new one
        template.is_active = False

        db.session.commit()
        flash(
            f"Template '{name}' v{new_version} created (previous version preserved for existing audits).",
            "success",
        )
        return redirect(url_for("templates.template_list"))

    # --- No existing audits: update in place ---
    template.name = name
    template.version = version or template.version
    template.description = description
    template.domain_type = domain_type
    template.compliance_framework = compliance_framework

    # Remove old sections (cascade deletes criteria, anchors, evidence)
    for section in template.sections.all():
        db.session.delete(section)
    # Remove old scoping questions (cascade deletes rules)
    for sq in ScopingQuestion.query.filter_by(template_id=template.id).all():
        db.session.delete(sq)
    db.session.flush()

    _build_template_from_sections(template, sections_data)

    # Parse and save scoping questions
    scoping_errors = _save_scoping_questions(template, request.form, sections_data)
    if scoping_errors:
        for err in scoping_errors:
            flash(err, "error")

    db.session.commit()

    flash(f"Template '{name}' updated.", "success")
    return redirect(url_for("templates.template_list"))


@templates_bp.route(
    "/admin/templates/<int:template_id>/toggle", methods=["POST"]
)
@roles_required("admin")
def template_toggle(template_id):
    """Toggle a template between active and inactive."""
    template = db.session.get(AuditTemplate, template_id)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("templates.template_list"))

    template.is_active = not template.is_active
    db.session.commit()

    state = "activated" if template.is_active else "deactivated"
    flash(f"Template '{template.name}' {state}.", "success")
    return redirect(url_for("templates.template_list"))


@templates_bp.route(
    "/admin/templates/<int:template_id>/delete", methods=["POST"]
)
@roles_required("admin")
def template_delete(template_id):
    """Delete a template if it has no audits referencing it."""
    template = db.session.get(AuditTemplate, template_id)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("templates.template_list"))

    if _template_has_audits(template_id):
        flash(
            f"Cannot delete '{template.name}' — it is used by existing audits. Deactivate it instead.",
            "error",
        )
        return redirect(url_for("templates.template_list"))

    name = template.name
    db.session.delete(template)
    db.session.commit()

    flash(f"Template '{name}' deleted.", "success")
    return redirect(url_for("templates.template_list"))


# ---------------------------------------------------------------------------
# JSON Import / Export / Sample
# ---------------------------------------------------------------------------


def _template_to_dict(template):
    """Serialize an AuditTemplate to a JSON-friendly dict."""
    sections = []
    for section in template.sections.order_by(TemplateSection.sort_order):
        criteria = []
        for crit in section.criteria.order_by(TemplateCriterion.sort_order):
            scoring = [
                {"score": a.score, "description": a.description}
                for a in crit.scoring_anchors.order_by(CriterionScoringAnchor.score)
            ]
            evidence = [
                {
                    "text": ev.text,
                    "is_required": ev.is_required,
                }
                for ev in crit.evidence_items.order_by(CriterionEvidenceItem.sort_order)
            ]
            criteria.append({
                "code": crit.code,
                "title": crit.title,
                "guidance": crit.guidance,
                "question": crit.question,
                "na_allowed": crit.na_allowed,
                "tip": crit.tip,
                "scoring": scoring,
                "evidence": evidence,
            })
        sections.append({"name": section.name, "criteria": criteria})
    # Serialize scoping questions and rules
    scoping_questions = []
    scoping_rules = []
    for sq in template.scoping_questions.order_by(ScopingQuestion.sort_order):
        options = None
        if sq.options_json:
            try:
                options = json.loads(sq.options_json)
            except (json.JSONDecodeError, TypeError):
                options = None
        scoping_questions.append({
            "identifier": sq.identifier,
            "question_text": sq.question_text,
            "answer_type": sq.answer_type,
            "options": options,
            "sort_order": sq.sort_order,
        })
        for rule in sq.rules.all():
            scoping_rules.append({
                "question_identifier": sq.identifier,
                "trigger_answer": rule.trigger_answer,
                "target_type": rule.target_type,
                "target_code": rule.target_code,
                "applicability_status": rule.applicability_status,
            })

    return {
        "name": template.name,
        "version": template.version,
        "description": template.description,
        "domain_type": template.domain_type,
        "compliance_framework": template.compliance_framework,
        "sections": sections,
        "scoping_questions": scoping_questions,
        "scoping_rules": scoping_rules,
    }


@templates_bp.route("/admin/templates/sample.json")
@roles_required("admin")
def template_sample_json():
    """Return a sample JSON showing the expected template format."""
    sample = {
        "name": "My Audit Template",
        "version": "1.0",
        "description": "Optional description of the template",
        "domain_type": "IT Security",
        "compliance_framework": "ISO 27001:2022",
        "sections": [
            {
                "name": "Section 1 — Management & Leadership",
                "criteria": [
                    {
                        "code": "C1",
                        "title": "Criterion title here",
                        "guidance": "Optional guidance text",
                        "question": "Optional assessment question",
                        "na_allowed": False,
                        "tip": "Optional tip for auditors",
                        "scoring": [
                            {"score": 0, "description": "Not implemented"},
                            {"score": 1, "description": "Partially implemented"},
                            {"score": 2, "description": "Mostly implemented"},
                            {"score": 3, "description": "Fully implemented"},
                            {"score": 4, "description": "Exceeds requirements"},
                        ],
                        "evidence": [
                            {"text": "Evidence item description", "is_required": False},
                            {"text": "Required evidence item", "is_required": True},
                        ],
                    }
                ],
            }
        ],
        "scoping_questions": [
            {
                "identifier": "q1",
                "question_text": "Does the organisation use cloud services?",
                "answer_type": "yes_no",
                "options": None,
                "sort_order": 0,
            }
        ],
        "scoping_rules": [
            {
                "question_identifier": "q1",
                "trigger_answer": "Yes",
                "target_type": "criterion",
                "target_code": "C1",
                "applicability_status": "applicable",
            }
        ],
    }
    return jsonify(sample)


@templates_bp.route("/admin/templates/<int:template_id>/export.json")
@roles_required("admin")
def template_export_json(template_id):
    """Export an existing template as JSON."""
    import unicodedata

    template = db.session.get(AuditTemplate, template_id)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("templates.template_list"))
    data = _template_to_dict(template)
    # Sanitize filename to ASCII for Content-Disposition header
    safe_name = unicodedata.normalize("NFKD", template.name).encode("ascii", "ignore").decode("ascii")
    safe_name = safe_name.replace(" ", "_") or "template"
    response = jsonify(data)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{safe_name}_v{template.version}.json"'
    )
    return response


@templates_bp.route("/admin/templates/import-json", methods=["POST"])
@roles_required("admin")
def template_import_json():
    """Import a template from an uploaded JSON file."""
    file = request.files.get("json_file")
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("templates.template_list"))

    try:
        data = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        flash(f"Invalid JSON file: {exc}", "error")
        return redirect(url_for("templates.template_list"))

    # Validate required fields
    name = (data.get("name") or "").strip()
    if not name:
        flash("JSON must include a 'name' field.", "error")
        return redirect(url_for("templates.template_list"))

    version = (data.get("version") or "1.0").strip()
    description = (data.get("description") or "").strip() or None
    sections_data = data.get("sections", [])

    if not isinstance(sections_data, list) or not sections_data:
        flash("JSON must include a non-empty 'sections' array.", "error")
        return redirect(url_for("templates.template_list"))

    # Build the template
    template = AuditTemplate(
        name=name,
        version=version,
        description=description,
        is_active=True,
        is_builtin=False,
        domain_type=(data.get("domain_type") or "").strip() or None,
        compliance_framework=(data.get("compliance_framework") or "").strip() or None,
    )
    db.session.add(template)
    db.session.flush()

    # Build sections from JSON (reuse the same structure as _build_template_from_sections)
    parsed_sections = []
    for sec in sections_data:
        sec_name = (sec.get("name") or "").strip()
        if not sec_name:
            continue
        criteria = []
        for crit in sec.get("criteria", []):
            code = (crit.get("code") or "").strip()
            title = (crit.get("title") or "").strip()
            if not code or not title:
                continue
            criteria.append({
                "code": code,
                "title": title,
                "guidance": crit.get("guidance"),
                "question": crit.get("question"),
                "na_allowed": bool(crit.get("na_allowed", False)),
                "tip": crit.get("tip"),
                "scoring": crit.get("scoring", []),
                "evidence": crit.get("evidence", []),
            })
        parsed_sections.append({"name": sec_name, "criteria": criteria})

    if not parsed_sections:
        db.session.rollback()
        flash("No valid sections found in JSON.", "error")
        return redirect(url_for("templates.template_list"))

    _build_template_from_sections(template, parsed_sections)

    # Collect valid criteria codes and section names for validation
    valid_criteria_codes = set()
    valid_section_names = set()
    for sec in parsed_sections:
        valid_section_names.add(sec["name"])
        for crit in sec.get("criteria", []):
            valid_criteria_codes.add(crit["code"])

    # Parse scoping questions
    scoping_questions_data = data.get("scoping_questions", [])
    scoping_rules_data = data.get("scoping_rules", [])

    if scoping_questions_data and isinstance(scoping_questions_data, list):
        # Build a map of question identifier -> ScopingQuestion for rule linking
        question_map = {}
        for idx, sq_data in enumerate(scoping_questions_data):
            identifier = (sq_data.get("identifier") or "").strip()
            question_text = (sq_data.get("question_text") or "").strip()
            answer_type = (sq_data.get("answer_type") or "").strip()
            if not identifier or not question_text or not answer_type:
                continue
            options = sq_data.get("options")
            options_json = json.dumps(options) if options else None
            sort_order = sq_data.get("sort_order", idx)

            sq = ScopingQuestion(
                template_id=template.id,
                identifier=identifier,
                question_text=question_text,
                answer_type=answer_type,
                options_json=options_json,
                sort_order=sort_order,
            )
            db.session.add(sq)
            question_map[identifier] = sq

        db.session.flush()

        # Validate scoping rules target_code references before creating them
        if scoping_rules_data and isinstance(scoping_rules_data, list):
            invalid_refs = []
            for rule_data in scoping_rules_data:
                target_type = (rule_data.get("target_type") or "").strip()
                target_code = (rule_data.get("target_code") or "").strip()
                if not target_code:
                    continue
                if target_type == "criterion" and target_code not in valid_criteria_codes:
                    invalid_refs.append(f"criterion '{target_code}'")
                elif target_type == "section" and target_code not in valid_section_names:
                    invalid_refs.append(f"section '{target_code}'")

            if invalid_refs:
                db.session.rollback()
                ref_list = ", ".join(invalid_refs)
                flash(
                    f"Import rejected: scoping rules reference invalid targets: {ref_list}",
                    "error",
                )
                return redirect(url_for("templates.template_list"))

            # Create scoping rules
            for rule_data in scoping_rules_data:
                q_identifier = (rule_data.get("question_identifier") or "").strip()
                trigger_answer = (rule_data.get("trigger_answer") or "").strip()
                target_type = (rule_data.get("target_type") or "").strip()
                target_code = (rule_data.get("target_code") or "").strip()
                applicability_status = (rule_data.get("applicability_status") or "").strip()
                if not q_identifier or not trigger_answer or not target_type or not target_code or not applicability_status:
                    continue
                question = question_map.get(q_identifier)
                if not question:
                    continue
                rule = ScopingRule(
                    question_id=question.id,
                    trigger_answer=trigger_answer,
                    target_type=target_type,
                    target_code=target_code,
                    applicability_status=applicability_status,
                )
                db.session.add(rule)

    db.session.commit()

    flash(f"Template '{name}' v{version} imported successfully.", "success")
    return redirect(url_for("templates.template_list"))
