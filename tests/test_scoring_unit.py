"""Unit tests for criteria scoring and auto-save API (task 7.1).

Covers:
- PUT /api/audits/<id>/score auto-save endpoint
- Reject modifications on Completed/Archived audits (Req 4.6)
- N/A handling: reject when na_allowed=False, require reason (Req 5.3)
- Auto-transition Draft→In_Progress on first score save (Req 4.2)
- Overall score recalculation after each save (Req 5.7)
- GET /audits/<id>/score/<code> scoring form route
"""

import pytest
from datetime import date

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.audit import Audit, AuditScore, EvidenceCheckState
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


def _create_template():
    """Create a template with one section, two criteria (MB1 na_allowed=False, MB2 na_allowed=True),
    scoring anchors, and evidence items."""
    template = AuditTemplate(
        name="Test Template", version="1.0", is_active=True
    )
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(
        template_id=template.id, name="Section 1", sort_order=1
    )
    _db.session.add(section)
    _db.session.flush()

    c1 = TemplateCriterion(
        section_id=section.id, code="MB1", title="Criterion 1",
        sort_order=1, na_allowed=False,
    )
    c2 = TemplateCriterion(
        section_id=section.id, code="MB2", title="Criterion 2",
        sort_order=2, na_allowed=True,
    )
    _db.session.add_all([c1, c2])
    _db.session.flush()

    # Add scoring anchors for c1
    for score_val in range(5):
        anchor = CriterionScoringAnchor(
            criterion_id=c1.id, score=score_val,
            description=f"Score {score_val} description",
        )
        _db.session.add(anchor)

    # Add evidence items to c1
    ev1 = CriterionEvidenceItem(
        criterion_id=c1.id, text="Evidence item 1", sort_order=1
    )
    ev2 = CriterionEvidenceItem(
        criterion_id=c1.id, text="Evidence item 2", sort_order=2
    )
    _db.session.add_all([ev1, ev2])
    _db.session.commit()
    return template


def _login(client, app, user):
    """Log in a user and set the session cookie."""
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit_with_scores(auditor, template, status="Draft"):
    """Create an audit with AuditScore and EvidenceCheckState rows."""
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
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

            evidence_items = criterion.evidence_items.order_by(
                CriterionEvidenceItem.sort_order
            ).all()
            for item in evidence_items:
                check_state = EvidenceCheckState(
                    audit_score_id=score.id,
                    evidence_item_id=item.id,
                    is_checked=False,
                )
                _db.session.add(check_state)

    _db.session.commit()
    _db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Auto-save endpoint tests
# ---------------------------------------------------------------------------


class TestAutoSaveEndpoint:
    """Tests for PUT /api/audits/<id>/score."""

    def test_save_score_persists_value(self, app, client):
        """Saving a score should persist it to the database."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB1",
                    "score": 3,
                    "is_na": False,
                    "notes": "Good compliance",
                    "evidence_checks": {},
                },
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["ok"] is True
            assert data["score"] == 3
            assert data["criterion_code"] == "MB1"

            # Verify persisted in DB
            score_record = AuditScore.query.filter_by(audit_id=audit.id).join(
                TemplateCriterion
            ).filter(TemplateCriterion.code == "MB1").first()
            assert score_record.score == 3
            assert score_record.notes == "Good compliance"

    def test_save_score_persists_evidence_checks(self, app, client):
        """Saving evidence checks should persist their state."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            # Get evidence item IDs for MB1
            criterion = TemplateCriterion.query.filter_by(code="MB1").first()
            ev_items = criterion.evidence_items.all()
            assert len(ev_items) >= 2

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB1",
                    "score": 2,
                    "is_na": False,
                    "evidence_checks": {
                        str(ev_items[0].id): True,
                        str(ev_items[1].id): False,
                    },
                },
            )
            assert resp.status_code == 200

            # Verify evidence check states
            score_record = AuditScore.query.filter_by(
                audit_id=audit.id, criterion_id=criterion.id
            ).first()
            states = {
                cs.evidence_item_id: cs.is_checked
                for cs in score_record.evidence_check_states.all()
            }
            assert states[ev_items[0].id] is True
            assert states[ev_items[1].id] is False

    def test_reject_modification_on_completed_audit(self, app, client):
        """Scoring on a Completed audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Completed")
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 3},
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_reject_modification_on_archived_audit(self, app, client):
        """Scoring on an Archived audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Archived")
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 3},
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()


    def test_reject_na_when_not_allowed(self, app, client):
        """Setting N/A on a criterion with na_allowed=False should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB1",  # na_allowed=False
                    "is_na": True,
                    "na_reason": "Not applicable",
                },
            )
            assert resp.status_code == 400
            assert "N/A" in resp.get_json()["error"]

    def test_na_allowed_requires_reason(self, app, client):
        """Setting N/A without a reason should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB2",  # na_allowed=True
                    "is_na": True,
                    "na_reason": "",
                },
            )
            assert resp.status_code == 400
            assert "reason" in resp.get_json()["error"].lower()

    def test_na_allowed_with_reason_succeeds(self, app, client):
        """Setting N/A with a valid reason on an na_allowed criterion should succeed."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB2",  # na_allowed=True
                    "is_na": True,
                    "na_reason": "Not relevant to this site",
                },
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["ok"] is True
            assert data["is_na"] is True

    def test_auto_transition_draft_to_in_progress(self, app, client):
        """First score save on a Draft audit should transition to In_Progress."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Draft")
            _login(client, app, user)

            assert audit.status == "Draft"

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 2},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["audit_status"] == "In_Progress"

            # Verify in DB
            _db.session.refresh(audit)
            assert audit.status == "In_Progress"

    def test_no_transition_when_already_in_progress(self, app, client):
        """Saving a score on an In_Progress audit should keep it In_Progress."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="In_Progress")
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 4},
            )
            assert resp.status_code == 200
            assert resp.get_json()["audit_status"] == "In_Progress"

    def test_overall_score_recalculated(self, app, client):
        """Overall score should be recalculated after each save."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            # Score MB1 = 4
            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 4},
            )
            assert resp.status_code == 200
            # Only MB1 scored, so overall = 4.0
            assert resp.get_json()["overall_score"] == 4.0

            # Score MB2 = 2
            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB2", "score": 2},
            )
            assert resp.status_code == 200
            # (4 + 2) / 2 = 3.0
            assert resp.get_json()["overall_score"] == 3.0

    def test_na_excluded_from_overall_score(self, app, client):
        """N/A criteria should be excluded from overall score calculation."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            # Score MB1 = 4
            client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 4},
            )

            # Mark MB2 as N/A
            client.put(
                f"/api/audits/{audit.id}/score",
                json={
                    "criterion_code": "MB2",
                    "is_na": True,
                    "na_reason": "Not applicable",
                },
            )

            _db.session.refresh(audit)
            # Only MB1 counted, so overall = 4.0
            assert audit.overall_score == 4.0

    def test_invalid_score_value_rejected(self, app, client):
        """Score values outside 0-4 should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": 5},
            )
            assert resp.status_code == 400

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "MB1", "score": -1},
            )
            assert resp.status_code == 400

    def test_nonexistent_audit_returns_404(self, app, client):
        """Scoring on a nonexistent audit should return 404."""
        with app.app_context():
            user = _create_user()
            _login(client, app, user)

            resp = client.put(
                "/api/audits/9999/score",
                json={"criterion_code": "MB1", "score": 3},
            )
            assert resp.status_code == 404

    def test_nonexistent_criterion_returns_404(self, app, client):
        """Scoring a nonexistent criterion code should return 404."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"criterion_code": "INVALID", "score": 3},
            )
            assert resp.status_code == 404

    def test_missing_criterion_code_returns_400(self, app, client):
        """Request without criterion_code should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                json={"score": 3},
            )
            assert resp.status_code == 400

    def test_invalid_json_body_returns_400(self, app, client):
        """Request with invalid JSON should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/score",
                data="not json",
                content_type="text/plain",
            )
            assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Scoring form route tests
# ---------------------------------------------------------------------------


class TestScoringFormRoute:
    """Tests for GET /audits/<id>/score/<code>."""

    def test_scoring_form_renders(self, app, client):
        """GET scoring form should return 200 with criterion data."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/score/MB1")
            assert resp.status_code == 200
            assert b"MB1" in resp.data
            assert b"Criterion 1" in resp.data

    def test_scoring_form_nonexistent_audit_returns_404(self, app, client):
        """Scoring form for nonexistent audit should return 404."""
        with app.app_context():
            user = _create_user()
            _login(client, app, user)

            resp = client.get("/audits/9999/score/MB1")
            assert resp.status_code == 404

    def test_scoring_form_nonexistent_criterion_returns_404(self, app, client):
        """Scoring form for nonexistent criterion code should return 404."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/score/INVALID")
            assert resp.status_code == 404

    def test_scoring_form_requires_auditor_role(self, app, client):
        """Scoring form should require auditor role."""
        with app.app_context():
            viewer = _create_user(roles="viewer", username="viewer1")
            template = _create_template()
            auditor = _create_user(roles="auditor", username="auditor1")
            audit = _create_audit_with_scores(auditor, template)
            _login(client, app, viewer)

            resp = client.get(f"/audits/{audit.id}/score/MB1")
            assert resp.status_code == 403
