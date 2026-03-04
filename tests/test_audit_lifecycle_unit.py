"""Unit tests for audit CRUD and state machine (task 6.1).

Covers:
- Audit creation with AuditScore rows
- Audit list filtering by role
- State machine transitions (valid and invalid)
- Rejection of modifications on Completed/Archived audits
"""

import pytest
from datetime import date

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.audit import Audit, AuditScore, AuditSignOff, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
    CriterionEvidenceItem,
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

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

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


def _create_user(roles="auditor", username="auditor1"):
    """Helper to create a user."""
    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        password_hash=hash_password("password123"),
        roles=roles,
        is_active=True,
    )
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user


def _create_template(active=True):
    """Helper to create a template with one section and two criteria."""
    template = AuditTemplate(
        name="Test Template",
        version="1.0",
        is_active=active,
    )
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(
        template_id=template.id, name="Section 1", sort_order=1
    )
    _db.session.add(section)
    _db.session.flush()

    c1 = TemplateCriterion(
        section_id=section.id, code="MB1", title="Criterion 1", sort_order=1
    )
    c2 = TemplateCriterion(
        section_id=section.id, code="MB2", title="Criterion 2", sort_order=2
    )
    _db.session.add_all([c1, c2])
    _db.session.flush()

    # Add an evidence item to c1
    ev = CriterionEvidenceItem(
        criterion_id=c1.id, text="Evidence item 1", sort_order=1
    )
    _db.session.add(ev)
    _db.session.commit()
    return template


def _login(client, app, user):
    """Log in a user and return the session cookie."""
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit(auditor, template, status="Draft", auditee=None):
    """Helper to create an audit directly in the DB."""
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        auditee_id=auditee.id if auditee else None,
        status=status,
        audit_date=date(2026, 1, 15),
    )
    _db.session.add(audit)
    _db.session.commit()
    _db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Audit creation tests
# ---------------------------------------------------------------------------


class TestAuditCreation:
    def test_create_audit_creates_score_rows(self, app, client):
        """Creating an audit should create AuditScore rows for all criteria."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            template_id = template.id
            _login(client, app, user)

        resp = client.post(
            "/audits/new",
            data={
                "template_id": template_id,
                "audit_date": "2026-03-01",
                "assessment_period": "Q1 2026",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302  # Redirect to detail

        with app.app_context():
            audit = Audit.query.first()
            assert audit is not None
            assert audit.status == "Draft"
            assert audit.scores.count() == 2  # Two criteria
            # All scores should be unscored (None)
            for score in audit.scores.all():
                assert score.score is None
                assert score.is_na is False

    def test_create_audit_creates_evidence_check_states(self, app, client):
        """Creating an audit should create EvidenceCheckState rows."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            template_id = template.id
            _login(client, app, user)

        client.post(
            "/audits/new",
            data={"template_id": template_id},
            follow_redirects=False,
        )

        with app.app_context():
            audit = Audit.query.first()
            # MB1 has 1 evidence item, MB2 has 0
            total_checks = EvidenceCheckState.query.count()
            assert total_checks == 1

    def test_create_audit_rejects_inactive_template(self, app, client):
        """Cannot create an audit with an inactive template."""
        with app.app_context():
            user = _create_user()
            template = _create_template(active=False)
            template_id = template.id
            _login(client, app, user)

        resp = client.post(
            "/audits/new",
            data={"template_id": template_id},
        )
        assert resp.status_code == 400

    def test_create_audit_requires_auditor_role(self, app, client):
        """Non-auditors cannot create audits."""
        with app.app_context():
            user = _create_user(roles="viewer", username="viewer1")
            _create_template()
            _login(client, app, user)

        resp = client.get("/audits/new")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Audit list filtering tests
# ---------------------------------------------------------------------------


class TestAuditListFiltering:
    def test_auditor_sees_all_audits(self, app, client):
        """Auditors see all audits regardless of status."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            _create_audit(auditor, template, status="Draft")
            _create_audit(auditor, template, status="Completed")
            _login(client, app, auditor)

        resp = client.get("/audits")
        assert resp.status_code == 200
        assert b"Draft" in resp.data
        assert b"Completed" in resp.data

    def test_auditee_sees_only_own_audits(self, app, client):
        """Auditees see only audits where they are the auditee."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            other = _create_user(roles="auditee", username="auditee2")
            template = _create_template()
            _create_audit(auditor, template, auditee=auditee)
            _create_audit(auditor, template, auditee=other)
            _login(client, app, auditee)

        resp = client.get("/audits")
        assert resp.status_code == 200
        # Should see 1 audit (their own), not 2
        data = resp.data.decode()
        assert data.count("<tr>") == 2  # header + 1 data row

    def test_viewer_sees_only_completed(self, app, client):
        """Viewers see only Completed audits."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            viewer = _create_user(roles="viewer", username="viewer1")
            template = _create_template()
            _create_audit(auditor, template, status="Draft")
            _create_audit(auditor, template, status="Completed")
            _login(client, app, viewer)

        resp = client.get("/audits")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert "Completed" in data
        assert data.count("<tr>") == 2  # header + 1 data row

    def test_admin_sees_all_audits(self, app, client):
        """Admins see all audits."""
        with app.app_context():
            admin = _create_user(roles="admin", username="admin1")
            auditor = _create_user(roles="auditor", username="auditor1")
            template = _create_template()
            _create_audit(auditor, template, status="Draft")
            _create_audit(auditor, template, status="In_Progress")
            _create_audit(auditor, template, status="Completed")
            _login(client, app, admin)

        resp = client.get("/audits")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert data.count("<tr>") == 4  # header + 3 data rows


# ---------------------------------------------------------------------------
# State machine tests
# ---------------------------------------------------------------------------


class TestStateMachine:
    def test_valid_transition_in_progress_to_review(self, app, client):
        """In_Progress → Review is a valid transition."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            audit = _create_audit(auditor, template, status="In_Progress")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/review", follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            audit = _db.session.get(Audit, audit_id)
            assert audit.status == "Review"

    def test_valid_transition_review_to_completed(self, app, client):
        """Review → Completed via finalise."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            audit = _create_audit(auditor, template, status="Review")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/finalise", follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            audit = _db.session.get(Audit, audit_id)
            assert audit.status == "Completed"
            # Sign-off should be created
            assert audit.sign_off is not None
            assert audit.sign_off.auditor_finalised_at is not None

    def test_valid_transition_completed_to_archived(self, app, client):
        """Completed → Archived via archive (admin only)."""
        with app.app_context():
            admin = _create_user(roles="admin", username="admin1")
            auditor = _create_user(roles="auditor", username="auditor1")
            template = _create_template()
            audit = _create_audit(auditor, template, status="Completed")
            _login(client, app, admin)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/archive", follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            audit = _db.session.get(Audit, audit_id)
            assert audit.status == "Archived"

    def test_invalid_transition_draft_to_review(self, app, client):
        """Draft → Review is invalid (must go through In_Progress first)."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            audit = _create_audit(auditor, template, status="Draft")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/review")
        assert resp.status_code == 400

        with app.app_context():
            audit = _db.session.get(Audit, audit_id)
            assert audit.status == "Draft"  # Unchanged

    def test_invalid_transition_draft_to_completed(self, app, client):
        """Draft → Completed is invalid."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            audit = _create_audit(auditor, template, status="Draft")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/finalise")
        assert resp.status_code == 400

    def test_invalid_transition_completed_to_review(self, app, client):
        """Completed → Review is invalid (no backward transitions)."""
        with app.app_context():
            auditor = _create_user()
            template = _create_template()
            audit = _create_audit(auditor, template, status="Completed")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/review")
        assert resp.status_code == 400

    def test_archive_requires_admin(self, app, client):
        """Only admins can archive audits."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            template = _create_template()
            audit = _create_audit(auditor, template, status="Completed")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/archive")
        assert resp.status_code == 403

    def test_invalid_transition_archived_to_anything(self, app, client):
        """Archived is a terminal state — no transitions allowed."""
        with app.app_context():
            admin = _create_user(roles="admin", username="admin1")
            auditor = _create_user(roles="auditor", username="auditor1")
            template = _create_template()
            audit = _create_audit(auditor, template, status="Archived")
            _login(client, app, auditor)
            audit_id = audit.id

        resp = client.post(f"/audits/{audit_id}/review")
        assert resp.status_code == 400

        resp = client.post(f"/audits/{audit_id}/finalise")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Audit detail access control tests
# ---------------------------------------------------------------------------


class TestAuditDetailAccess:
    def test_auditee_can_view_own_audit(self, app, client):
        """Auditees can view audits where they are the auditee."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee)
            _login(client, app, auditee)
            audit_id = audit.id

        resp = client.get(f"/audits/{audit_id}")
        assert resp.status_code == 200

    def test_auditee_cannot_view_others_audit(self, app, client):
        """Auditees cannot view audits where they are not the auditee."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            other = _create_user(roles="auditee", username="auditee2")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=other)
            _login(client, app, auditee)
            audit_id = audit.id

        resp = client.get(f"/audits/{audit_id}")
        assert resp.status_code == 403

    def test_viewer_can_view_completed_audit(self, app, client):
        """Viewers can view Completed audits."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            viewer = _create_user(roles="viewer", username="viewer1")
            template = _create_template()
            audit = _create_audit(auditor, template, status="Completed")
            _login(client, app, viewer)
            audit_id = audit.id

        resp = client.get(f"/audits/{audit_id}")
        assert resp.status_code == 200

    def test_viewer_cannot_view_draft_audit(self, app, client):
        """Viewers cannot view non-Completed audits."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            viewer = _create_user(roles="viewer", username="viewer1")
            template = _create_template()
            audit = _create_audit(auditor, template, status="Draft")
            _login(client, app, viewer)
            audit_id = audit.id

        resp = client.get(f"/audits/{audit_id}")
        assert resp.status_code == 403

    def test_nonexistent_audit_returns_404(self, app, client):
        """Requesting a non-existent audit returns 404."""
        with app.app_context():
            auditor = _create_user()
            _login(client, app, auditor)

        resp = client.get("/audits/9999")
        assert resp.status_code == 404
