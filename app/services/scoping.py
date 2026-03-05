"""Scoping engine service.

Evaluates scoping rules against answers, produces criterion applicability
records, persists scoping profiles, and handles re-scoping when answers change.
"""

from __future__ import annotations

import logging

from app.extensions import db
from app.models.audit import Audit, AuditScore
from app.models.scoping import (
    CriterionApplicability,
    ScopingProfile,
    ScopingQuestion,
)
from app.models.template import AuditTemplate

logger = logging.getLogger(__name__)


def evaluate_scoping(audit_id: int, answers: dict[str, str]) -> dict:
    """Evaluate scoping rules for an audit given question answers.

    Args:
        audit_id: The audit to scope.
        answers: Mapping of question identifier → answer value.

    Returns:
        {
            "applicable_count": int,
            "not_applicable_count": int,
            "total_count": int,
            "criteria": {criterion_id: "applicable" | "not_applicable"},
        }
    """
    audit = db.session.get(Audit, audit_id)
    template = db.session.get(AuditTemplate, audit.template_id)

    # Build lookup of all criteria in the template, defaulting to "applicable"
    criteria_map: dict[int, str] = {}
    # Build code → criterion_id and section_name → list[criterion_id] lookups
    code_to_id: dict[str, int] = {}
    section_criteria: dict[str, list[int]] = {}

    for section in template.sections.all():
        section_crit_ids: list[int] = []
        for criterion in section.criteria.all():
            criteria_map[criterion.id] = "applicable"
            code_to_id[criterion.code] = criterion.id
            section_crit_ids.append(criterion.id)
        section_criteria[section.name] = section_crit_ids

    # Build identifier → question lookup
    questions = {
        q.identifier: q
        for q in ScopingQuestion.query.filter_by(template_id=template.id).all()
    }

    # Evaluate each rule
    for identifier, question in questions.items():
        answer = answers.get(identifier)
        if answer is None:
            continue

        for rule in question.rules.all():
            if rule.trigger_answer != answer:
                continue

            if rule.target_type == "criterion":
                crit_id = code_to_id.get(rule.target_code)
                if crit_id is None:
                    logger.warning(
                        "Scoping rule %d references non-existent criterion code '%s' — skipping",
                        rule.id,
                        rule.target_code,
                    )
                    continue
                criteria_map[crit_id] = rule.applicability_status

            elif rule.target_type == "section":
                crit_ids = section_criteria.get(rule.target_code)
                if crit_ids is None:
                    logger.warning(
                        "Scoping rule %d references non-existent section '%s' — skipping",
                        rule.id,
                        rule.target_code,
                    )
                    continue
                for cid in crit_ids:
                    criteria_map[cid] = rule.applicability_status

    total = len(criteria_map)
    applicable = sum(1 for s in criteria_map.values() if s == "applicable")
    not_applicable = total - applicable

    return {
        "applicable_count": applicable,
        "not_applicable_count": not_applicable,
        "total_count": total,
        "criteria": criteria_map,
    }


def persist_scoping_profile(audit_id: int, answers: dict[str, str]) -> None:
    """Save or update scoping answers for an audit.

    Upserts a ScopingProfile row for each question identifier / answer pair.
    """
    audit = db.session.get(Audit, audit_id)
    template_id = audit.template_id

    # Map identifier → question id
    questions = {
        q.identifier: q.id
        for q in ScopingQuestion.query.filter_by(template_id=template_id).all()
    }

    for identifier, answer_value in answers.items():
        question_id = questions.get(identifier)
        if question_id is None:
            continue

        existing = ScopingProfile.query.filter_by(
            audit_id=audit_id, question_id=question_id
        ).first()

        if existing:
            existing.answer_value = answer_value
        else:
            db.session.add(
                ScopingProfile(
                    audit_id=audit_id,
                    question_id=question_id,
                    answer_value=answer_value,
                )
            )

    db.session.commit()


def persist_applicability(audit_id: int, applicability: dict[int, str]) -> None:
    """Save or update criterion applicability records for an audit.

    Args:
        audit_id: The audit.
        applicability: Mapping of criterion_id → "applicable" | "not_applicable".
    """
    for criterion_id, status in applicability.items():
        existing = CriterionApplicability.query.filter_by(
            audit_id=audit_id, criterion_id=criterion_id
        ).first()

        if existing:
            existing.applicability_status = status
        else:
            db.session.add(
                CriterionApplicability(
                    audit_id=audit_id,
                    criterion_id=criterion_id,
                    applicability_status=status,
                )
            )

    db.session.commit()


def get_applicable_criteria(audit_id: int) -> list[int]:
    """Return list of criterion IDs that are applicable for this audit."""
    rows = CriterionApplicability.query.filter_by(
        audit_id=audit_id, applicability_status="applicable"
    ).all()
    return [r.criterion_id for r in rows]


def clear_scores_for_newly_applicable(
    audit_id: int, old_app: dict, new_app: dict
) -> None:
    """Clear scores for criteria that changed from not_applicable to applicable.

    When re-scoping, any criterion that was previously scoped out but is now
    applicable needs its score cleared so the auditor must re-score it.

    Args:
        audit_id: The audit.
        old_app: Previous applicability map {criterion_id: status}.
        new_app: New applicability map {criterion_id: status}.
    """
    for criterion_id, new_status in new_app.items():
        old_status = old_app.get(criterion_id)
        if old_status == "not_applicable" and new_status == "applicable":
            AuditScore.query.filter_by(
                audit_id=audit_id, criterion_id=criterion_id
            ).delete()

    db.session.commit()
