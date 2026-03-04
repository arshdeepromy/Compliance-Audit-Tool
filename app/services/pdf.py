"""PDF report generation service.

Renders an audit report as HTML via Jinja2, then converts to PDF using
WeasyPrint.  If WeasyPrint is not installed (missing system dependencies),
falls back to returning the rendered HTML as a downloadable file.
"""

from flask import current_app, render_template

from app.extensions import db
from app.models.audit import Audit, AuditScore, AuditSignOff
from app.models.action import CorrectiveAction
from app.models.settings import BrandingSettings
from app.models.template import (
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User


def generate_audit_pdf(audit_id: int) -> tuple[bytes, str, str]:
    """Generate a PDF (or HTML fallback) report for the given audit.

    Returns:
        (content_bytes, content_type, filename)
    """
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        raise ValueError(f"Audit {audit_id} not found")

    # Load related data
    template = audit.template
    auditor = db.session.get(User, audit.auditor_id)
    auditee = db.session.get(User, audit.auditee_id) if audit.auditee_id else None

    # Branding
    branding = db.session.get(BrandingSettings, 1)
    if branding is None:
        branding_data = {
            "company_name": current_app.config.get(
                "DEFAULT_COMPANY_NAME", "Tōtika Audit Tool"
            ),
            "primary_colour": "#f97316",
            "accent_colour": "#fb923c",
            "logo_filename": None,
        }
    else:
        branding_data = {
            "company_name": branding.company_name,
            "primary_colour": branding.primary_colour,
            "accent_colour": branding.accent_colour,
            "logo_filename": branding.logo_filename,
        }

    # Build section data with criteria and scores
    sections_data = []
    all_scores = []
    sections = (
        TemplateSection.query
        .filter_by(template_id=template.id)
        .order_by(TemplateSection.sort_order)
        .all()
    )

    for section in sections:
        criteria_data = []
        criteria = (
            TemplateCriterion.query
            .filter_by(section_id=section.id)
            .order_by(TemplateCriterion.sort_order)
            .all()
        )
        for criterion in criteria:
            score_record = AuditScore.query.filter_by(
                audit_id=audit.id, criterion_id=criterion.id
            ).first()
            score_val = None
            notes = ""
            is_na = False
            if score_record:
                score_val = score_record.score
                notes = score_record.notes or ""
                is_na = score_record.is_na
                all_scores.append(score_record)

            criteria_data.append({
                "code": criterion.code,
                "title": criterion.title,
                "score": score_val,
                "notes": notes,
                "is_na": is_na,
            })

        # Section average
        scored = [c for c in criteria_data if c["score"] is not None and not c["is_na"]]
        section_avg = (
            sum(c["score"] for c in scored) / len(scored) if scored else None
        )
        section_gap_count = sum(
            1 for c in criteria_data
            if c["score"] is not None and not c["is_na"] and c["score"] < 2
        )

        sections_data.append({
            "name": section.name,
            "criteria": criteria_data,
            "average": section_avg,
            "gap_count": section_gap_count,
            "criteria_count": len(criteria_data),
        })

    # Score distribution
    scored_records = [
        s for s in all_scores if s.score is not None and not s.is_na
    ]
    total_scored = len(scored_records)
    distribution = {i: 0 for i in range(5)}
    for s in scored_records:
        distribution[s.score] = distribution.get(s.score, 0) + 1

    na_count = sum(1 for s in all_scores if s.is_na)
    total_criteria = len(all_scores)

    # Gap summary: criteria scored < 3
    gap_items = []
    for s in all_scores:
        if s.score is not None and not s.is_na and s.score < 3:
            criterion = db.session.get(TemplateCriterion, s.criterion_id)
            if s.score == 0:
                priority = "critical"
            elif s.score == 1:
                priority = "high"
            else:
                priority = "medium"

            actions = CorrectiveAction.query.filter_by(
                audit_id=audit.id, criterion_code=criterion.code
            ).all()
            action_status = "No action"
            if actions:
                statuses = [a.status for a in actions]
                if all(st == "Completed" for st in statuses):
                    action_status = "Completed"
                elif any(st == "Overdue" for st in statuses):
                    action_status = "Overdue"
                elif any(st == "In_Progress" for st in statuses):
                    action_status = "In Progress"
                else:
                    action_status = "Open"

            gap_items.append({
                "code": criterion.code,
                "title": criterion.title,
                "score": s.score,
                "priority": priority,
                "action_status": action_status,
            })

    # Sign-off
    sign_off = audit.sign_off

    # Render HTML template
    html_content = render_template(
        "pdf/report.html",
        audit=audit,
        template=template,
        auditor=auditor,
        auditee=auditee,
        branding=branding_data,
        sections=sections_data,
        distribution=distribution,
        total_scored=total_scored,
        total_criteria=total_criteria,
        na_count=na_count,
        gap_items=gap_items,
        sign_off=sign_off,
    )

    filename_base = f"audit-{audit.id}-report"

    # Try WeasyPrint conversion
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        return (pdf_bytes, "application/pdf", f"{filename_base}.pdf")
    except ImportError:
        # WeasyPrint not available — return HTML fallback
        return (
            html_content.encode("utf-8"),
            "text/html",
            f"{filename_base}.html",
        )
