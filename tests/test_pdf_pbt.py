"""Property-based tests for PDF report export.

Feature: totika-audit-webapp
Property 20: PDF export contains all required audit data

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 9.1, 9.2, 9.5**
"""

import html as html_mod
import itertools
from datetime import date

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.settings import BrandingSettings
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SCORES = [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = itertools.count()


def _uid():
    return next(_counter)


def _make_app(tmp_path):
    """Create a fresh Flask app with its own SQLite DB."""
    uid = _uid()
    upload_dir = tmp_path / f"uploads_{uid}"
    upload_dir.mkdir()

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'pdf_pbt_{uid}.db'}"
        UPLOAD_FOLDER = str(upload_dir)

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_user(app, roles="auditor", display_name=None):
    """Create a user and return (user_id, display_name, token)."""
    uid = _uid()
    username = f"user_{uid}"
    name = display_name or f"User {uid}"
    with app.app_context():
        user = User(
            username=username,
            email=f"{username}@example.com",
            display_name=name,
            password_hash=hash_password("test-pw"),
            roles=roles,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user.id, name, token


def _make_branding(app, company_name):
    """Create branding settings with the given company name."""
    with app.app_context():
        branding = BrandingSettings(
            id=1,
            company_name=company_name,
            primary_colour="#ff6600",
            accent_colour="#ff9933",
            logo_filename=None,
        )
        db.session.add(branding)
        db.session.commit()


def _make_template(app, num_criteria):
    """Create a template with a single section and the given number of criteria.

    Returns (template_id, template_name, list of criterion codes).
    """
    uid = _uid()
    template_name = f"Template {uid}"
    with app.app_context():
        template = AuditTemplate(name=template_name, version="1.0", is_active=True)
        db.session.add(template)
        db.session.flush()

        section = TemplateSection(
            template_id=template.id, name="Safety Section", sort_order=1
        )
        db.session.add(section)
        db.session.flush()

        codes = []
        for i in range(1, num_criteria + 1):
            code = f"MB{i}"
            c = TemplateCriterion(
                section_id=section.id,
                code=code,
                title=f"Criterion {i}",
                sort_order=i,
                na_allowed=False,
            )
            db.session.add(c)
            db.session.flush()

            for score_val in range(5):
                db.session.add(
                    CriterionScoringAnchor(
                        criterion_id=c.id,
                        score=score_val,
                        description=f"Score {score_val} desc",
                    )
                )

            db.session.add(
                CriterionEvidenceItem(
                    criterion_id=c.id, text=f"Evidence {i}", sort_order=1
                )
            )
            codes.append(code)

        db.session.commit()
        return template.id, template_name, codes


def _make_audit_with_scores(app, user_id, template_id, scores_list):
    """Create an audit and assign scores to criteria in order.

    scores_list: list of int scores (0-4), one per criterion.
    Returns audit_id.
    """
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=user_id,
            status="In_Progress",
            audit_date=date(2026, 3, 15),
            assessment_period="Q1 2026",
        )
        db.session.add(audit)
        db.session.flush()

        sections = TemplateSection.query.filter_by(template_id=template_id).all()
        score_idx = 0
        for section in sections:
            criteria = (
                TemplateCriterion.query.filter_by(section_id=section.id)
                .order_by(TemplateCriterion.sort_order)
                .all()
            )
            for criterion in criteria:
                score_val = scores_list[score_idx] if score_idx < len(scores_list) else None
                score = AuditScore(
                    audit_id=audit.id,
                    criterion_id=criterion.id,
                    score=score_val,
                )
                db.session.add(score)
                db.session.flush()

                for item in criterion.evidence_items.order_by(
                    CriterionEvidenceItem.sort_order
                ).all():
                    db.session.add(
                        EvidenceCheckState(
                            audit_score_id=score.id,
                            evidence_item_id=item.id,
                            is_checked=False,
                        )
                    )
                score_idx += 1

        # Calculate overall score
        scored = [s for s in scores_list if s is not None]
        if scored:
            audit.overall_score = sum(scored) / len(scored)

        db.session.commit()
        return audit.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Number of criteria: 2 to 8
st_num_criteria = st.integers(min_value=2, max_value=8)

# Score for a criterion: 0-4
st_score = st.integers(min_value=0, max_value=4)

# Company name: printable ASCII, 3-40 chars, no HTML-special chars
st_company_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        whitelist_characters="-_&",
    ),
    min_size=3,
    max_size=40,
).filter(lambda s: s.strip() and any(c.isalpha() for c in s))


# ---------------------------------------------------------------------------
# Property 20: PDF export contains all required audit data
# ---------------------------------------------------------------------------


class TestProperty20PDFExportContainsRequiredData:
    """**Validates: Requirements 9.1, 9.2, 9.5**

    For any audit with scored criteria, the PDF/HTML output should contain:
    - Company name from branding settings
    - Template name
    - Auditor's display name
    - All criterion codes (MB1, MB2, etc.)
    - All non-null scores
    - Gap items for criteria scored < 3
    """

    @given(
        num_criteria=st_num_criteria,
        data=st.data(),
        company_name=st_company_name,
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_pdf_contains_all_required_audit_data(
        self, tmp_path, num_criteria, data, company_name
    ):
        """PDF output contains company name, template name, auditor name,
        all criterion codes, and gap items for scores < 3."""
        # Generate a score for each criterion
        scores = [data.draw(st_score) for _ in range(num_criteria)]

        app = _make_app(tmp_path)
        user_id, auditor_name, token = _make_user(app)
        _make_branding(app, company_name)
        template_id, template_name, codes = _make_template(app, num_criteria)
        audit_id = _make_audit_with_scores(app, user_id, template_id, scores)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.get(f"/audits/{audit_id}/pdf")

        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}"
        )
        assert "attachment" in resp.headers.get("Content-Disposition", ""), (
            "Response should have Content-Disposition: attachment"
        )

        content = resp.data.decode("utf-8")

        # 1. Company name present (HTML-escaped since content is HTML)
        escaped_company_name = html_mod.escape(company_name)
        assert escaped_company_name in content, (
            f"Company name '{company_name}' (escaped: '{escaped_company_name}') not found in PDF output"
        )

        # 2. Template name present
        assert template_name in content, (
            f"Template name '{template_name}' not found in PDF output"
        )

        # 3. Auditor display name present
        assert auditor_name in content, (
            f"Auditor name '{auditor_name}' not found in PDF output"
        )

        # 4. All criterion codes present
        for code in codes:
            assert code in content, (
                f"Criterion code '{code}' not found in PDF output"
            )

        # 5. Gap items: criteria scored < 3 should appear in gap summary
        gap_codes = [
            codes[i] for i, s in enumerate(scores) if s < 3
        ]
        non_gap_codes = [
            codes[i] for i, s in enumerate(scores) if s >= 3
        ]

        # The gap summary section lists criteria scored below 3.
        # Extract the gap summary portion of the HTML (after "Gap Summary" heading).
        gap_section_marker = "Gap Summary"
        assert gap_section_marker in content, (
            "PDF output should contain a 'Gap Summary' section"
        )

        gap_section_start = content.index(gap_section_marker)
        gap_section = content[gap_section_start:]

        for code in gap_codes:
            assert code in gap_section, (
                f"Gap code '{code}' (score < 3) not found in Gap Summary section"
            )

        # Non-gap criteria (score >= 3) should NOT appear in the gap table.
        # They do appear in the criteria detail above, so we check specifically
        # within the gap table portion.
        # The gap table ends before the Sign-Off section or end of document.
        gap_table_end_markers = ["Sign-Off", "</body>"]
        gap_end = len(gap_section)
        for marker in gap_table_end_markers:
            idx = gap_section.find(marker)
            if idx != -1 and idx < gap_end:
                gap_end = idx
        gap_table_content = gap_section[:gap_end]

        for code in non_gap_codes:
            assert code not in gap_table_content, (
                f"Non-gap code '{code}' (score >= 3) should NOT appear in Gap Summary"
            )
