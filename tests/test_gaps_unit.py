"""Unit tests for gap checklist and corrective action CRUD (task 9.1).

Covers:
- GET /audits/<id>/gaps — gap list returns only criteria scored 0 or 1
- POST /api/audits/<id>/actions — corrective action creation
- PUT /api/audits/<id>/actions/<aid> — corrective action status update
- Completion records completed_at and completed_by
- Rejection on Completed/Archived audits
- Priority and status filtering
"""

import pytest
from datetime import date, datetime

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.action import CorrectiveAction
from app.models.audit import Audit, AuditScore, EvidenceCheckState
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


def _create_template_with_criteria():
    """Create a template with 4 criteria for testing gap filtering."""
    template = AuditTemplate(name="Test Template", version="1.0", is_active=True)
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(template_id=template.id, name="Section 1", sort_order=1)
    _db.session.add(section)
    _db.session.flush()

    # MB1: will be scored 0 (critical gap)
    c1 = TemplateCriterion(section_id=section.id, code="MB1", title="Criterion 1", sort_order=1, na_allowed=False)
    # MB2: will be scored 1 (high gap)
    c2 = TemplateCriterion(section_id=section.id, code="MB2", title="Criterion 2", sort_order=2, na_allowed=False)
    # MB3: will be scored 3 (not a gap)
    c3 = TemplateCriterion(section_id=section.id, code="MB3", title="Criterion 3", sort_order=3, na_allowed=False)
    # MB4: will be scored 4 (not a gap)
    c4 = TemplateCriterion(section_id=section.id, code="MB4", title="Criterion 4", sort_order=4, na_allowed=False)
    _db.session.add_all([c1, c2, c3, c4])
    _db.session.commit()
    return template


def _login(client, app, user):
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit_with_scores(auditor, template, status="In_Progress", scores=None):
    """Create an audit with specific scores. scores is a dict of code -> score value."""
    if scores is None:
        scores = {"MB1": 0, "MB2": 1, "MB3": 3, "MB4": 4}

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
            score_val = scores.get(criterion.code)
            score = AuditScore(
                audit_id=audit.id,
                criterion_id=criterion.id,
                score=score_val,
            )
            _db.session.add(score)

    _db.session.commit()
    _db.session.refresh(audit)
    return audit


# ---------------------------------------------------------------------------
# Gap list tests
# ---------------------------------------------------------------------------


class TestGapList:
    """Tests for GET /audits/<id>/gaps."""

    def test_gap_list_returns_only_score_0_and_1(self, app, client):
        """Gap list should contain only criteria scored 0 or 1."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/gaps")
            assert resp.status_code == 200
            html = resp.data.decode()
            # Check gap cards in the main content area (sidebar shows all criteria)
            assert 'data-criterion-code="MB1"' in html  # score 0 = critical
            assert 'data-criterion-code="MB2"' in html  # score 1 = high
            assert 'data-criterion-code="MB3"' not in html  # score 3 = not a gap
            assert 'data-criterion-code="MB4"' not in html  # score 4 = not a gap

    def test_gap_list_priority_filter_critical(self, app, client):
        """Filtering by priority=critical should show only score 0 criteria."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/gaps?priority=critical")
            assert resp.status_code == 200
            html = resp.data.decode()
            assert 'data-criterion-code="MB1"' in html
            assert 'data-criterion-code="MB2"' not in html

    def test_gap_list_priority_filter_high(self, app, client):
        """Filtering by priority=high should show only score 1 criteria."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/gaps?priority=high")
            assert resp.status_code == 200
            html = resp.data.decode()
            assert 'data-criterion-code="MB2"' in html
            assert 'data-criterion-code="MB1"' not in html

    def test_gap_list_status_filter(self, app, client):
        """Filtering by status should show only gaps with matching corrective actions."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            # Create a corrective action for MB1 with status Open
            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix this",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()

            _login(client, app, user)

            # Filter by Open — should show MB1 (has Open action)
            resp = client.get(f"/audits/{audit.id}/gaps?status=Open")
            assert resp.status_code == 200
            html = resp.data.decode()
            assert 'data-criterion-code="MB1"' in html
            # MB2 has no actions, so it should be filtered out
            assert 'data-criterion-code="MB2"' not in html

    def test_gap_list_shows_summary_counts(self, app, client):
        """Gap list should display corrective action summary counts."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            # Create actions with different statuses
            for status in ["Open", "In_Progress", "Completed"]:
                action = CorrectiveAction(
                    audit_id=audit.id,
                    criterion_code="MB1",
                    description=f"Action {status}",
                    priority="critical",
                    status=status,
                )
                _db.session.add(action)
            _db.session.commit()

            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/gaps")
            assert resp.status_code == 200
            html = resp.data.decode()
            assert "Total: 3" in html
            assert "Open: 1" in html
            assert "In Progress: 1" in html
            assert "Completed: 1" in html
            assert "Overdue: 0" in html

    def test_gap_list_nonexistent_audit_returns_404(self, app, client):
        """Gap list for nonexistent audit should return 404."""
        with app.app_context():
            user = _create_user()
            _login(client, app, user)

            resp = client.get("/audits/9999/gaps")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Corrective action creation tests
# ---------------------------------------------------------------------------


class TestCreateAction:
    """Tests for POST /api/audits/<id>/actions."""

    def test_create_action_success(self, app, client):
        """Creating a corrective action should return 201 with action data."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "description": "Implement safety policy",
                    "priority": "critical",
                    "due_date": "2026-06-01",
                },
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["ok"] is True
            assert data["action"]["criterion_code"] == "MB1"
            assert data["action"]["description"] == "Implement safety policy"
            assert data["action"]["status"] == "Open"
            assert data["action"]["priority"] == "critical"
            assert data["action"]["due_date"] == "2026-06-01"

    def test_create_action_persists_to_db(self, app, client):
        """Created action should be persisted in the database."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "description": "Fix gap",
                    "priority": "critical",
                },
            )

            action = CorrectiveAction.query.filter_by(audit_id=audit.id).first()
            assert action is not None
            assert action.description == "Fix gap"
            assert action.status == "Open"

    def test_create_action_rejected_on_completed_audit(self, app, client):
        """Creating action on Completed audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template, status="Completed")
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "description": "Fix gap",
                    "priority": "critical",
                },
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_create_action_rejected_on_archived_audit(self, app, client):
        """Creating action on Archived audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template, status="Archived")
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "description": "Fix gap",
                    "priority": "critical",
                },
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_create_action_missing_description(self, app, client):
        """Creating action without description should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "priority": "critical",
                },
            )
            assert resp.status_code == 400
            assert "description" in resp.get_json()["error"].lower()

    def test_create_action_missing_criterion_code(self, app, client):
        """Creating action without criterion_code should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "description": "Fix gap",
                    "priority": "critical",
                },
            )
            assert resp.status_code == 400
            assert "criterion_code" in resp.get_json()["error"].lower()

    def test_create_action_with_assigned_user(self, app, client):
        """Creating action with assigned_to_id should persist it."""
        with app.app_context():
            user = _create_user()
            assignee = _create_user(roles="auditor", username="assignee1")
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.post(
                f"/api/audits/{audit.id}/actions",
                json={
                    "criterion_code": "MB1",
                    "description": "Fix gap",
                    "assigned_to_id": assignee.id,
                    "priority": "critical",
                },
            )
            assert resp.status_code == 201
            assert resp.get_json()["action"]["assigned_to_id"] == assignee.id


# ---------------------------------------------------------------------------
# Corrective action update tests
# ---------------------------------------------------------------------------


class TestUpdateAction:
    """Tests for PUT /api/audits/<id>/actions/<aid>."""

    def test_update_action_status(self, app, client):
        """Updating action status should persist the change."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix gap",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"status": "In_Progress"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["action"]["status"] == "In_Progress"

    def test_completion_records_completed_at_and_by(self, app, client):
        """Setting status to Completed should record completed_at and completed_by."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix gap",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"status": "Completed"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["action"]["status"] == "Completed"
            assert data["action"]["completed_at"] is not None
            assert data["action"]["completed_by_id"] == user.id

            # Verify in DB
            _db.session.refresh(action)
            assert action.completed_at is not None
            assert action.completed_by_id == user.id

    def test_moving_away_from_completed_clears_fields(self, app, client):
        """Changing status from Completed to another should clear completion fields."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix gap",
                priority="critical",
                status="Completed",
                completed_at=datetime.utcnow(),
                completed_by_id=user.id,
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"status": "Open"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["action"]["completed_at"] is None
            assert data["action"]["completed_by_id"] is None

    def test_update_action_rejected_on_completed_audit(self, app, client):
        """Updating action on Completed audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template, status="Completed")

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix gap",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"status": "In_Progress"},
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_update_action_rejected_on_archived_audit(self, app, client):
        """Updating action on Archived audit should return 400."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template, status="Archived")

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Fix gap",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"status": "In_Progress"},
            )
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_update_nonexistent_action_returns_404(self, app, client):
        """Updating a nonexistent action should return 404."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/9999",
                json={"status": "In_Progress"},
            )
            assert resp.status_code == 404

    def test_update_action_description(self, app, client):
        """Updating action description should persist the change."""
        with app.app_context():
            user = _create_user()
            template = _create_template_with_criteria()
            audit = _create_audit_with_scores(user, template)

            action = CorrectiveAction(
                audit_id=audit.id,
                criterion_code="MB1",
                description="Original description",
                priority="critical",
                status="Open",
            )
            _db.session.add(action)
            _db.session.commit()
            action_id = action.id

            _login(client, app, user)

            resp = client.put(
                f"/api/audits/{audit.id}/actions/{action_id}",
                json={"description": "Updated description"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["action"]["description"] == "Updated description"
