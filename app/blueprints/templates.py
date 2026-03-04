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


def _increment_version(version_str):
    """Increment a version string, e.g. '1.0' → '2.0', '3' → '4'."""
    parts = version_str.split(".")
    try:
        parts[0] = str(int(parts[0]) + 1)
    except (ValueError, IndexError):
        return version_str + ".1"
    return ".".join(parts)


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
    )
    db.session.add(template)
    db.session.flush()

    _build_template_from_sections(template, sections_data)
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
        )
        db.session.add(new_template)
        db.session.flush()

        _build_template_from_sections(new_template, sections_data)

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

    # Remove old sections (cascade deletes criteria, anchors, evidence)
    for section in template.sections.all():
        db.session.delete(section)
    db.session.flush()

    _build_template_from_sections(template, sections_data)
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
    return {
        "name": template.name,
        "version": template.version,
        "description": template.description,
        "sections": sections,
    }


@templates_bp.route("/admin/templates/sample.json")
@roles_required("admin")
def template_sample_json():
    """Return a sample JSON showing the expected template format."""
    sample = {
        "name": "My Audit Template",
        "version": "1.0",
        "description": "Optional description of the template",
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
    db.session.commit()

    flash(f"Template '{name}' v{version} imported successfully.", "success")
    return redirect(url_for("templates.template_list"))
