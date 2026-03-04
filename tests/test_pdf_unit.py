"""Unit tests for PDF report generation (task 11.1).

Covers:
- PDF route returns 200 with content
- PDF contains audit metadata
- PDF contains criterion scores
- PDF contains gap summary
- Non-existent audit returns 404
"""

import pytest
from datetime import date, datetime

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.audit import Audit, AuditScore, AuditSignOff, EvidenceCheckState
from app.models.action import CorrectiveAction
from app.models.settings import BrandingSettings
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with a file-based SQLite DB."""
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        UPLOAD_FOLDER = str(upload_dir)

    application = create_app(config_class=Cfg, run_startup=False)
    return application


@pytest.fixture(autouse=True)
def setup_db(app):
    with app.app_context():
        _db.create_all()
        yield
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(roles="auditor", username="auditor1"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.replace("_", " ").title(),
        password_hash=hash_password("password123"),
        roles=roles,
        is_active=True,
    )
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user


def _create_branding():
    branding = BrandingSettings(
        id=1,
        company_name="Acme Safety Ltd",
        primary_colour="#ff6600",
        accent_colour="#ff9933",
        logo_filename=None,
    )
    _db.session.add(branding)
    _db.session.commit()
    return branding


def _create_template_with_criteria(num_criteria=3):
    """Create a template with a single section and the given number of criteria."""
    template = AuditTemplate(name="Test Template", version="1.0", is_active=True)
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(template_id=template.id, name="Safety Management", sort_order=1)
    _db.session.add(section)
    _db.session.flush()

    criteria = []
    for i in range(1, num_criteria + 1):
        c = TemplateCriterion(
            section_id=section.id,
            code=f"MB{i}",
            title=f"Criterion {i}",
            sort_order=i,
            na_allowed=False,
        )
        _db.session.add(c)
        _db.session.flush()

        for score_val in range(5):
            _db.session.add(CriterionScoringAnchor(
                criterion_id=c.id, score=score_val,
                description=f"Score {score_val} description",
            ))

        ev = CriterionEvidenceItem(criterion_id=c.id, text=f"Evidence {i}", sort_order=1)
        _db.session.add(ev)
        criteria.append(c)

    _db.session.commit()
    return template, section, criteria


def _login(client, app, user):
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit_with_scores(auditor, template, criteria, scores_map=None, status="In_Progress"):
    """Create an audit with scored criteria.

    scores_map: dict of criterion_code -> score value (e.g. {"MB1": 4, "MB2": 1})
    """
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        status=status,
        audit_date=date(2026, 3, 15),
        assessment_period="Q1 2026",
    )
    _db.session.add(audit)
    _db.session.flush()

    for criterion in criteria:
        score_val = None
        if scores_map and criterion.code in scores_map:
            score_val = scores_map[criterion.code]

        score = AuditScore(
            audit_id=audit.id,
            criterion_id=criterion.id,
            score=score_val,
        )
        _db.session.add(score)
        _db.session.flush()

        for item in criterion.evidence_items.order_by(CriterionEvidenceItem.sort_order).all():
            _db.session.add(EvidenceCheckState(
                audit_score_id=score.id, evidence_item_id=item.id, is_checked=False,
            ))

    # Calculate overall score
    scored = [s for s in (scores_map or {}).values() if s is not None]
    if scored:
        audit.overall_score = sum(scored) / len(scored)

    _db.session.commit()
    _db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPDFRoute:
    """Tests for GET /audits/<id>/pdf."""

    def test_pdf_route_returns_200(self, app, client):
        """PDF route returns 200 with downloadable content."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(3)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 4, "MB2": 3, "MB3": 2},
            )
            audit_id = audit.id
            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("Content-Disposition", "")

    def test_pdf_contains_audit_metadata(self, app, client):
        """PDF content includes audit metadata (auditor name, date, period)."""
        with app.app_context():
            user = _create_user(roles="auditor", username="jane_auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(2)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 3, "MB2": 4},
            )
            audit_id = audit.id
            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        assert resp.status_code == 200
        content = resp.data.decode("utf-8")

        # Check metadata is present
        assert "Jane Auditor" in content
        assert "2026-03-15" in content
        assert "Q1 2026" in content
        assert "Acme Safety Ltd" in content
        assert "Test Template" in content

    def test_pdf_contains_criterion_scores(self, app, client):
        """PDF content includes criterion codes and scores."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(3)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 4, "MB2": 2, "MB3": 0},
            )
            audit_id = audit.id
            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        content = resp.data.decode("utf-8")

        assert "MB1" in content
        assert "MB2" in content
        assert "MB3" in content
        assert "Criterion 1" in content
        assert "Criterion 2" in content
        assert "Criterion 3" in content

    def test_pdf_contains_gap_summary(self, app, client):
        """PDF includes gap summary for criteria scored < 3."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(4)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 4, "MB2": 0, "MB3": 1, "MB4": 2},
            )
            audit_id = audit.id

            # Add a corrective action for MB2
            action = CorrectiveAction(
                audit_id=audit_id,
                criterion_code="MB2",
                description="Fix safety policy",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()

            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        content = resp.data.decode("utf-8")

        # Gap summary should list MB2 (score 0), MB3 (score 1), MB4 (score 2)
        assert "Gap Summary" in content
        assert "Critical" in content or "critical" in content
        # MB2 has a corrective action with status Open
        assert "Open" in content

    def test_nonexistent_audit_returns_404(self, app, client):
        """Requesting PDF for a non-existent audit returns 404."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _login(client, app, user)

        resp = client.get("/audits/99999/pdf")
        assert resp.status_code == 404

    def test_pdf_accessible_to_admin(self, app, client):
        """Admin users can access the PDF route."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            admin = _create_user(roles="admin", username="admin1")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(2)
            audit = _create_audit_with_scores(
                auditor, template, criteria,
                scores_map={"MB1": 3, "MB2": 4},
            )
            audit_id = audit.id
            _login(client, app, admin)

        resp = client.get(f"/audits/{audit_id}/pdf")
        assert resp.status_code == 200

    def test_pdf_contains_sign_off_info(self, app, client):
        """PDF includes sign-off information when available."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(2)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 4, "MB2": 3},
                status="Completed",
            )
            # Add sign-off
            sign_off = AuditSignOff(
                audit_id=audit.id,
                auditor_finalised_at=datetime(2026, 3, 20, 10, 0),
                auditee_acknowledged_at=datetime(2026, 3, 21, 14, 30),
                auditee_typed_name="John Smith",
                auditee_comments="All findings accepted.",
            )
            _db.session.add(sign_off)
            _db.session.commit()
            audit_id = audit.id
            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        content = resp.data.decode("utf-8")

        assert "Sign-Off" in content
        assert "John Smith" in content
        assert "All findings accepted" in content

    def test_pdf_contains_section_summary(self, app, client):
        """PDF includes section summary table."""
        with app.app_context():
            user = _create_user(roles="auditor")
            _create_branding()
            template, section, criteria = _create_template_with_criteria(3)
            audit = _create_audit_with_scores(
                user, template, criteria,
                scores_map={"MB1": 4, "MB2": 3, "MB3": 2},
            )
            audit_id = audit.id
            _login(client, app, user)

        resp = client.get(f"/audits/{audit_id}/pdf")
        content = resp.data.decode("utf-8")

        assert "Section Summary" in content
        assert "Safety Management" in content
