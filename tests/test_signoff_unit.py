"""Unit tests for audit sign-off workflow (task 12.1).

Covers:
- Sign-off form accessible to auditee (Req 10.2)
- Sign-off records acknowledgement data (Req 10.3)
- Sign-off rejected on Draft/In_Progress audits
- Sign-off status displayed on detail page (Req 10.4)
"""

import pytest
from datetime import date, datetime

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.audit import Audit, AuditScore, AuditSignOff, EvidenceCheckState
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(roles="auditee", username="auditee1"):
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


def _create_template():
    template = AuditTemplate(name="Test Template", version="1.0", is_active=True)
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(template_id=template.id, name="Section 1", sort_order=1)
    _db.session.add(section)
    _db.session.flush()

    c1 = TemplateCriterion(
        section_id=section.id, code="MB1", title="Criterion 1",
        sort_order=1, na_allowed=False,
    )
    _db.session.add(c1)
    _db.session.flush()

    for score_val in range(5):
        _db.session.add(CriterionScoringAnchor(
            criterion_id=c1.id, score=score_val,
            description=f"Score {score_val} description",
        ))

    ev1 = CriterionEvidenceItem(criterion_id=c1.id, text="Evidence 1", sort_order=1)
    _db.session.add(ev1)
    _db.session.commit()
    return template


def _login(client, app, user):
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit(auditor, template, auditee=None, status="Review"):
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        auditee_id=auditee.id if auditee else None,
        status=status,
        audit_date=date(2026, 1, 15),
    )
    _db.session.add(audit)
    _db.session.flush()

    sections = template.sections.order_by(TemplateSection.sort_order).all()
    for section in sections:
        criteria = section.criteria.order_by(TemplateCriterion.sort_order).all()
        for criterion in criteria:
            score = AuditScore(audit_id=audit.id, criterion_id=criterion.id)
            _db.session.add(score)
            _db.session.flush()
            for item in criterion.evidence_items.order_by(CriterionEvidenceItem.sort_order).all():
                _db.session.add(EvidenceCheckState(
                    audit_score_id=score.id, evidence_item_id=item.id, is_checked=False,
                ))

    _db.session.commit()
    _db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Tests: Sign-off form accessible to auditee
# ---------------------------------------------------------------------------


class TestSignoffAccess:
    """Test that the sign-off form is accessible to the assigned auditee."""

    def test_auditee_can_access_signoff_form(self, app, client):
        """Auditee assigned to audit can GET the sign-off page."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, auditee)

            resp = client.get(f"/audits/{audit.id}/signoff")
            assert resp.status_code == 200
            assert b"Sign-off" in resp.data

    def test_admin_can_access_signoff_form(self, app, client):
        """Admin can access sign-off form for any audit."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            admin = _create_user(roles="admin", username="admin1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, admin)

            resp = client.get(f"/audits/{audit.id}/signoff")
            assert resp.status_code == 200

    def test_wrong_auditee_rejected(self, app, client):
        """Auditee not assigned to audit gets 403."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            other_auditee = _create_user(roles="auditee", username="auditee2")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, other_auditee)

            resp = client.get(f"/audits/{audit.id}/signoff")
            assert resp.status_code == 403

    def test_viewer_cannot_access_signoff(self, app, client):
        """Viewer role cannot access sign-off form."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            viewer = _create_user(roles="viewer", username="viewer1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, viewer)

            resp = client.get(f"/audits/{audit.id}/signoff")
            assert resp.status_code == 403

    def test_signoff_on_completed_audit(self, app, client):
        """Auditee can access sign-off on Completed audit."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Completed")
            _login(client, app, auditee)

            resp = client.get(f"/audits/{audit.id}/signoff")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Sign-off records acknowledgement data
# ---------------------------------------------------------------------------


class TestSignoffSubmission:
    """Test that sign-off POST records acknowledgement data correctly."""

    def test_signoff_records_data(self, app, client):
        """POST to sign-off records typed name, comments, and timestamp."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, auditee)

            resp = client.post(
                f"/audits/{audit.id}/signoff",
                data={"typed_name": "Jane Doe", "comments": "All looks good"},
                follow_redirects=False,
            )
            assert resp.status_code == 302

            # Verify data was persisted
            sign_off = AuditSignOff.query.filter_by(audit_id=audit.id).first()
            assert sign_off is not None
            assert sign_off.auditee_typed_name == "Jane Doe"
            assert sign_off.auditee_comments == "All looks good"
            assert sign_off.auditee_acknowledged_at is not None

    def test_signoff_requires_typed_name(self, app, client):
        """POST without typed name returns 400."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, auditee)

            resp = client.post(
                f"/audits/{audit.id}/signoff",
                data={"typed_name": "", "comments": ""},
            )
            assert resp.status_code == 400

    def test_signoff_updates_existing_record(self, app, client):
        """If a sign-off record already exists (from auditor finalise), update it."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")

            # Pre-create sign-off record (as if auditor finalised)
            sign_off = AuditSignOff(
                audit_id=audit.id,
                auditor_finalised_at=datetime(2026, 1, 20, 10, 0),
            )
            _db.session.add(sign_off)
            _db.session.commit()

            _login(client, app, auditee)

            resp = client.post(
                f"/audits/{audit.id}/signoff",
                data={"typed_name": "John Smith", "comments": "Acknowledged"},
                follow_redirects=False,
            )
            assert resp.status_code == 302

            updated = AuditSignOff.query.filter_by(audit_id=audit.id).first()
            assert updated.auditee_typed_name == "John Smith"
            assert updated.auditee_comments == "Acknowledged"
            assert updated.auditee_acknowledged_at is not None
            # Auditor finalisation should be preserved
            assert updated.auditor_finalised_at is not None

    def test_signoff_comments_optional(self, app, client):
        """Sign-off with empty comments stores None."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, auditee)

            resp = client.post(
                f"/audits/{audit.id}/signoff",
                data={"typed_name": "Jane Doe", "comments": ""},
                follow_redirects=False,
            )
            assert resp.status_code == 302

            sign_off = AuditSignOff.query.filter_by(audit_id=audit.id).first()
            assert sign_off.auditee_typed_name == "Jane Doe"
            assert sign_off.auditee_comments is None


# ---------------------------------------------------------------------------
# Tests: Sign-off rejected on Draft/In_Progress audits
# ---------------------------------------------------------------------------


class TestSignoffStatusRestriction:
    """Test that sign-off is rejected for audits not in Review/Completed."""

    def test_signoff_rejected_on_draft(self, app, client):
        """GET sign-off on Draft audit redirects with error."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Draft")
            _login(client, app, auditee)

            resp = client.get(f"/audits/{audit.id}/signoff", follow_redirects=False)
            assert resp.status_code == 302

    def test_signoff_rejected_on_in_progress(self, app, client):
        """GET sign-off on In_Progress audit redirects with error."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="In_Progress")
            _login(client, app, auditee)

            resp = client.get(f"/audits/{audit.id}/signoff", follow_redirects=False)
            assert resp.status_code == 302

    def test_post_signoff_rejected_on_draft(self, app, client):
        """POST sign-off on Draft audit redirects with error."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Draft")
            _login(client, app, auditee)

            resp = client.post(
                f"/audits/{audit.id}/signoff",
                data={"typed_name": "Jane", "comments": ""},
                follow_redirects=False,
            )
            assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Tests: Sign-off status displayed on detail page
# ---------------------------------------------------------------------------


class TestSignoffStatusDisplay:
    """Test that sign-off status is displayed on the audit detail page."""

    def test_detail_shows_signoff_status_after_finalise(self, app, client):
        """Detail page shows auditor finalised timestamp."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Completed")

            sign_off = AuditSignOff(
                audit_id=audit.id,
                auditor_finalised_at=datetime(2026, 1, 20, 10, 0),
            )
            _db.session.add(sign_off)
            _db.session.commit()

            _login(client, app, auditor)

            resp = client.get(f"/audits/{audit.id}")
            assert resp.status_code == 200
            assert b"Sign-off Status" in resp.data
            assert b"Auditor Finalised" in resp.data

    def test_detail_shows_auditee_acknowledged(self, app, client):
        """Detail page shows auditee acknowledged timestamp and name."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Completed")

            sign_off = AuditSignOff(
                audit_id=audit.id,
                auditor_finalised_at=datetime(2026, 1, 20, 10, 0),
                auditee_acknowledged_at=datetime(2026, 1, 21, 14, 30),
                auditee_typed_name="Jane Doe",
                auditee_comments="Looks good",
            )
            _db.session.add(sign_off)
            _db.session.commit()

            _login(client, app, auditor)

            resp = client.get(f"/audits/{audit.id}")
            assert resp.status_code == 200
            assert b"Jane Doe" in resp.data
            assert b"Auditee Acknowledged" in resp.data

    def test_detail_shows_pending_when_no_signoff(self, app, client):
        """Detail page shows sign-off section with Pending for Review audits."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="auditor1")
            auditee = _create_user(roles="auditee", username="auditee1")
            template = _create_template()
            audit = _create_audit(auditor, template, auditee=auditee, status="Review")
            _login(client, app, auditor)

            resp = client.get(f"/audits/{audit.id}")
            assert resp.status_code == 200
            assert b"Sign-off Status" in resp.data
            assert b"Pending" in resp.data
