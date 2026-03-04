"""Tests for Tōtika Category 2 template seeding."""

import pytest

from app.extensions import db
from app.models.template import (
    AuditTemplate,
    TemplateSection,
    TemplateCriterion,
    CriterionScoringAnchor,
    CriterionEvidenceItem,
)
from app.startup import seed_totika_template
from app.seed_data.totika_cat2 import (
    TEMPLATE_NAME,
    TEMPLATE_VERSION,
    SECTIONS,
    CRITERIA,
)


class TestSeedTotikaTemplate:
    """Tests for the seed_totika_template startup function."""

    def test_creates_template_on_empty_db(self, app):
        """Template is created when no built-in template exists."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            assert template is not None
            assert template.name == TEMPLATE_NAME
            assert template.version == TEMPLATE_VERSION
            assert template.is_active is True
            assert template.is_builtin is True

    def test_creates_all_13_sections(self, app):
        """All 13 sections are created with correct names and order."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            sections = TemplateSection.query.filter_by(
                template_id=template.id
            ).order_by(TemplateSection.sort_order).all()

            assert len(sections) == 13
            for i, sec in enumerate(sections):
                assert sec.name == SECTIONS[i]["name"]
                assert sec.sort_order == i

    def test_creates_all_54_criteria(self, app):
        """All 54 criteria (MB1–MB54) are created."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            sections = TemplateSection.query.filter_by(
                template_id=template.id
            ).all()
            section_ids = [s.id for s in sections]

            criteria = TemplateCriterion.query.filter(
                TemplateCriterion.section_id.in_(section_ids)
            ).all()
            assert len(criteria) == 54

            codes = {c.code for c in criteria}
            for i in range(1, 55):
                assert f"MB{i}" in codes

    def test_criteria_have_scoring_anchors(self, app):
        """Each criterion has scoring anchors (0–4)."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            sections = TemplateSection.query.filter_by(
                template_id=template.id
            ).all()
            section_ids = [s.id for s in sections]

            criteria = TemplateCriterion.query.filter(
                TemplateCriterion.section_id.in_(section_ids)
            ).all()

            for criterion in criteria:
                anchors = CriterionScoringAnchor.query.filter_by(
                    criterion_id=criterion.id
                ).all()
                expected_count = len(CRITERIA[criterion.code]["scoring"])
                assert len(anchors) == expected_count, (
                    f"{criterion.code} expected {expected_count} anchors, got {len(anchors)}"
                )

    def test_criteria_have_evidence_items(self, app):
        """Each criterion has the correct number of evidence items."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            sections = TemplateSection.query.filter_by(
                template_id=template.id
            ).all()
            section_ids = [s.id for s in sections]

            criteria = TemplateCriterion.query.filter(
                TemplateCriterion.section_id.in_(section_ids)
            ).all()

            for criterion in criteria:
                items = CriterionEvidenceItem.query.filter_by(
                    criterion_id=criterion.id
                ).all()
                expected_count = len(CRITERIA[criterion.code]["evidence"])
                assert len(items) == expected_count, (
                    f"{criterion.code} expected {expected_count} evidence items, got {len(items)}"
                )

    def test_na_allowed_flags_match_source(self, app):
        """na_allowed flags match the original tool data."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()
            sections = TemplateSection.query.filter_by(
                template_id=template.id
            ).all()
            section_ids = [s.id for s in sections]

            criteria = TemplateCriterion.query.filter(
                TemplateCriterion.section_id.in_(section_ids)
            ).all()

            for criterion in criteria:
                expected = CRITERIA[criterion.code]["na_allowed"]
                assert criterion.na_allowed == expected, (
                    f"{criterion.code} na_allowed: expected {expected}, got {criterion.na_allowed}"
                )

    def test_idempotent_no_duplicates(self, app):
        """Running seed twice does not create duplicate templates."""
        seed_totika_template(app)
        seed_totika_template(app)

        with app.app_context():
            templates = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).all()
            assert len(templates) == 1

    def test_mb1_data_integrity(self, app):
        """Spot-check MB1 criterion data matches the source."""
        seed_totika_template(app)

        with app.app_context():
            criterion = TemplateCriterion.query.filter_by(code="MB1").first()
            assert criterion is not None
            assert criterion.title == "H&S Policy"
            assert criterion.na_allowed is False
            assert criterion.guidance is not None
            assert "policy" in criterion.guidance.lower()

            anchors = CriterionScoringAnchor.query.filter_by(
                criterion_id=criterion.id
            ).order_by(CriterionScoringAnchor.score).all()
            assert len(anchors) == 5
            assert anchors[0].score == 0
            assert anchors[4].score == 4

    def test_section_criteria_grouping(self, app):
        """Criteria are grouped into the correct sections."""
        seed_totika_template(app)

        with app.app_context():
            template = AuditTemplate.query.filter_by(
                name=TEMPLATE_NAME, is_builtin=True
            ).first()

            # Check first section: Leadership & Commitment has MB1-MB6
            section = TemplateSection.query.filter_by(
                template_id=template.id, name="Leadership & Commitment"
            ).first()
            assert section is not None

            criteria = TemplateCriterion.query.filter_by(
                section_id=section.id
            ).order_by(TemplateCriterion.sort_order).all()
            codes = [c.code for c in criteria]
            assert codes == ["MB1", "MB2", "MB3", "MB4", "MB5", "MB6"]
