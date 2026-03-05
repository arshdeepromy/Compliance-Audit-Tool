"""Compliance engine service.

Computes domain scores, heatmap data, trend indicators, and control area
breakdowns from completed audit data for the compliance matrix dashboard.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func

from app.extensions import db
from app.models.audit import Audit, AuditScore
from app.models.scoping import CriterionApplicability
from app.models.template import AuditTemplate, TemplateCriterion, TemplateSection


def score_to_colour(score: float | None) -> str:
    """Map a score value to a heatmap colour string.

    Ranges:
        0.0–1.4 → "red"
        1.5–2.4 → "amber"
        2.5–3.4 → "light-green"
        3.5–4.0 → "green"
        None    → "grey"
    """
    if score is None:
        return "grey"
    if score < 1.5:
        return "red"
    if score < 2.5:
        return "amber"
    if score < 3.5:
        return "light-green"
    return "green"


def _get_most_recent_completed_audits() -> dict[str, Audit]:
    """Return the most recent Completed audit for each compliance framework.

    Returns:
        Mapping of compliance_framework → Audit (the most recent completed one).
    """
    # Subquery: max updated_at per (template.compliance_framework) among Completed audits
    subq = (
        db.session.query(
            AuditTemplate.compliance_framework,
            func.max(Audit.updated_at).label("max_date"),
        )
        .join(Audit, Audit.template_id == AuditTemplate.id)
        .filter(Audit.status == "Completed")
        .filter(AuditTemplate.compliance_framework.isnot(None))
        .group_by(AuditTemplate.compliance_framework)
        .subquery()
    )

    rows = (
        db.session.query(Audit)
        .join(AuditTemplate, Audit.template_id == AuditTemplate.id)
        .join(
            subq,
            db.and_(
                AuditTemplate.compliance_framework == subq.c.compliance_framework,
                Audit.updated_at == subq.c.max_date,
            ),
        )
        .filter(Audit.status == "Completed")
        .all()
    )

    result: dict[str, Audit] = {}
    for audit in rows:
        fw = audit.template.compliance_framework
        if fw and fw not in result:
            result[fw] = audit
    return result


def _get_previous_completed_audit(framework: str, before_audit: Audit) -> Audit | None:
    """Return the completed audit immediately before *before_audit* for the same framework."""
    return (
        db.session.query(Audit)
        .join(AuditTemplate, Audit.template_id == AuditTemplate.id)
        .filter(
            AuditTemplate.compliance_framework == framework,
            Audit.status == "Completed",
            Audit.updated_at < before_audit.updated_at,
        )
        .order_by(Audit.updated_at.desc())
        .first()
    )


def _compute_trend(current_score: float | None, previous_score: float | None) -> str | None:
    """Compute trend direction from two scores."""
    if current_score is None or previous_score is None:
        return None
    if current_score > previous_score:
        return "up"
    if current_score < previous_score:
        return "down"
    return "flat"


def _applicable_criteria_count(audit_id: int) -> int:
    """Count applicable criteria for an audit.

    If no CriterionApplicability records exist (no scoping was done), count all
    criteria in the audit's template.
    """
    count = CriterionApplicability.query.filter_by(
        audit_id=audit_id, applicability_status="applicable"
    ).count()
    if count > 0:
        return count

    # No scoping records — all criteria are applicable
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return 0
    return (
        db.session.query(func.count(TemplateCriterion.id))
        .join(TemplateSection, TemplateCriterion.section_id == TemplateSection.id)
        .filter(TemplateSection.template_id == audit.template_id)
        .scalar()
    ) or 0


def get_compliance_matrix() -> dict:
    """Compute the full compliance matrix data.

    Returns::

        {
            "domains": [
                {
                    "domain_type": str,
                    "frameworks": [
                        {
                            "framework": str,
                            "score": float | None,
                            "trend": "up" | "down" | "flat" | None,
                            "audit_id": int | None,
                            "cell_colour": str,
                        }
                    ],
                    "domain_avg": float | None,
                }
            ],
            "overall_score": float | None,
        }
    """
    most_recent = _get_most_recent_completed_audits()

    # Gather all templates that have a domain_type and compliance_framework
    templates = (
        AuditTemplate.query
        .filter(AuditTemplate.domain_type.isnot(None))
        .filter(AuditTemplate.compliance_framework.isnot(None))
        .all()
    )

    # Build domain → set of frameworks from templates
    domain_frameworks: dict[str, set[str]] = defaultdict(set)
    for t in templates:
        domain_frameworks[t.domain_type].add(t.compliance_framework)

    # Build domain rows
    domains: list[dict] = []
    all_weighted_scores: list[tuple[float, int]] = []  # (score, weight)

    for domain_type in sorted(domain_frameworks.keys()):
        frameworks_list: list[dict] = []
        domain_scores: list[float] = []

        for fw in sorted(domain_frameworks[domain_type]):
            audit = most_recent.get(fw)
            score = audit.overall_score if audit else None
            trend = None
            audit_id = None

            if audit:
                audit_id = audit.id
                prev = _get_previous_completed_audit(fw, audit)
                prev_score = prev.overall_score if prev else None
                trend = _compute_trend(score, prev_score)

            frameworks_list.append({
                "framework": fw,
                "score": score,
                "trend": trend,
                "audit_id": audit_id,
                "cell_colour": score_to_colour(score),
            })

            if score is not None:
                domain_scores.append(score)
                weight = _applicable_criteria_count(audit.id) if audit else 0
                if weight > 0:
                    all_weighted_scores.append((score, weight))

        domain_avg = (
            sum(domain_scores) / len(domain_scores) if domain_scores else None
        )

        domains.append({
            "domain_type": domain_type,
            "frameworks": frameworks_list,
            "domain_avg": domain_avg,
        })

    # Overall weighted score
    overall_score = None
    if all_weighted_scores:
        total_weight = sum(w for _, w in all_weighted_scores)
        if total_weight > 0:
            overall_score = sum(s * w for s, w in all_weighted_scores) / total_weight

    return {
        "domains": domains,
        "overall_score": overall_score,
    }


def get_trend_data(framework: str) -> list[dict]:
    """Return historical scores for all Completed audits of a framework.

    Returns a list sorted by date ascending::

        [{"audit_id": int, "date": str (ISO), "score": float}, ...]
    """
    audits = (
        db.session.query(Audit)
        .join(AuditTemplate, Audit.template_id == AuditTemplate.id)
        .filter(
            AuditTemplate.compliance_framework == framework,
            Audit.status == "Completed",
        )
        .order_by(Audit.updated_at.asc())
        .all()
    )

    return [
        {
            "audit_id": a.id,
            "date": a.updated_at.isoformat() if a.updated_at else None,
            "score": a.overall_score,
        }
        for a in audits
    ]


def get_control_area_breakdown(audit_id: int) -> list[dict]:
    """Return per-section scores for an audit.

    For each section in the audit's template, computes:
    - avg_score: average score of scored applicable criteria
    - applicable_count: number of applicable criteria
    - scored_count: number of applicable criteria that have a score
    - gap_count: number of scored criteria with score 0 or 1
    - colour: heatmap colour based on avg_score

    Returns::

        [
            {
                "section_name": str,
                "avg_score": float | None,
                "applicable_count": int,
                "scored_count": int,
                "gap_count": int,
                "colour": str,
            },
            ...
        ]
    """
    audit = db.session.get(Audit, audit_id)
    if audit is None:
        return []

    template = db.session.get(AuditTemplate, audit.template_id)
    if template is None:
        return []

    # Build set of not-applicable criterion IDs for this audit
    not_applicable_ids: set[int] = set()
    for ca in CriterionApplicability.query.filter_by(
        audit_id=audit_id, applicability_status="not_applicable"
    ).all():
        not_applicable_ids.add(ca.criterion_id)

    # Build criterion_id → score lookup
    score_map: dict[int, int | None] = {}
    for s in AuditScore.query.filter_by(audit_id=audit_id).all():
        score_map[s.criterion_id] = s.score

    result: list[dict] = []
    for section in template.sections.order_by(TemplateSection.sort_order).all():
        applicable_count = 0
        scored_count = 0
        gap_count = 0
        score_sum = 0.0

        for criterion in section.criteria.all():
            if criterion.id in not_applicable_ids:
                continue
            applicable_count += 1

            score_val = score_map.get(criterion.id)
            if score_val is not None:
                scored_count += 1
                score_sum += score_val
                if score_val <= 1:
                    gap_count += 1

        avg_score = score_sum / scored_count if scored_count > 0 else None

        result.append({
            "section_name": section.name,
            "avg_score": avg_score,
            "applicable_count": applicable_count,
            "scored_count": scored_count,
            "gap_count": gap_count,
            "colour": score_to_colour(avg_score),
        })

    return result
