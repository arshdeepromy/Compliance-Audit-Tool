"""Unit tests for the template management blueprint (task 5.2).

Covers:
- Admin-only access (RBAC)
- Template CRUD (list, create, edit)
- Template versioning when audits exist
- Active/inactive toggle
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.audit import Audit
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import Session, User
from app.utils.auth import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_admin(db_session):
    """Create an admin user and return (user, raw_token)."""
    user = User(
        username="admin_tpl",
        email="admin_tpl@example.com",
        display_name="Admin",
        password_hash=hash_password("password"),
        roles="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    raw_token = secrets.token_hex(32)
    session = Session(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=8),
        last_active_at=datetime.utcnow(),
    )
    db_session.add(session)
    db_session.commit()
    return user, raw_token


def _create_auditor(db_session):
    """Create an auditor user and return (user, raw_token)."""
    user = User(
        username="auditor_tpl",
        email="auditor_tpl@example.com",
        display_name="Auditor",
        password_hash=hash_password("password"),
        roles="auditor",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    raw_token = secrets.token_hex(32)
    session = Session(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=8),
        last_active_at=datetime.utcnow(),
    )
    db_session.add(session)
    db_session.commit()
    return user, raw_token


def _create_template(db_session, name="Test Template", version="1.0", is_active=True):
    """Create a minimal template with one section and one criterion."""
    tpl = AuditTemplate(
        name=name, version=version, is_active=is_active, is_builtin=False
    )
    db_session.add(tpl)
    db_session.flush()

    section = TemplateSection(template_id=tpl.id, name="Section 1", sort_order=0)
    db_session.add(section)
    db_session.flush()

    criterion = TemplateCriterion(
        section_id=section.id,
        code="T1",
        title="Test Criterion",
        sort_order=1,
    )
    db_session.add(criterion)
    db_session.flush()

    db_session.add(
        CriterionScoringAnchor(
            criterion_id=criterion.id, score=0, description="No evidence"
        )
    )
    db_session.add(
        CriterionEvidenceItem(
            criterion_id=criterion.id, text="Evidence A", sort_order=0
        )
    )
    db_session.commit()
    return tpl


# ---------------------------------------------------------------------------
# Tests: RBAC — admin-only access
# ---------------------------------------------------------------------------


class TestTemplateRBAC:
    """Non-admin users should be blocked from template management."""

    def test_auditor_cannot_list_templates(self, app, client):
        with app.app_context():
            _, token = _create_auditor(db.session)
        client.set_cookie("session_token", token)
        resp = client.get("/admin/templates")
        assert resp.status_code == 403

    def test_auditor_cannot_create_template(self, app, client):
        with app.app_context():
            _, token = _create_auditor(db.session)
        client.set_cookie("session_token", token)
        resp = client.post("/admin/templates/new", data={"name": "X", "version": "1"})
        assert resp.status_code == 403

    def test_auditor_cannot_toggle_template(self, app, client):
        with app.app_context():
            _, token = _create_auditor(db.session)
            tpl = _create_template(db.session)
            tpl_id = tpl.id
        client.set_cookie("session_token", token)
        resp = client.post(f"/admin/templates/{tpl_id}/toggle")
        assert resp.status_code == 403

    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/admin/templates")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# Tests: Template list
# ---------------------------------------------------------------------------


class TestTemplateList:
    def test_list_templates(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
            _create_template(db.session, name="Template A")
            _create_template(db.session, name="Template B")
        client.set_cookie("session_token", token)
        resp = client.get("/admin/templates")
        assert resp.status_code == 200
        assert b"Template A" in resp.data
        assert b"Template B" in resp.data


# ---------------------------------------------------------------------------
# Tests: Template creation
# ---------------------------------------------------------------------------


class TestTemplateCreate:
    def test_get_new_form(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
        client.set_cookie("session_token", token)
        resp = client.get("/admin/templates/new")
        assert resp.status_code == 200

    def test_create_template(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
        client.set_cookie("session_token", token)
        resp = client.post(
            "/admin/templates/new",
            data={
                "name": "New Template",
                "version": "1.0",
                "description": "A test template",
                "section_0_name": "Section One",
                "section_0_criterion_0_code": "C1",
                "section_0_criterion_0_title": "Criterion One",
                "section_0_criterion_0_score_0": "No evidence",
                "section_0_criterion_0_score_4": "Full compliance",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            tpl = AuditTemplate.query.filter_by(name="New Template").first()
            assert tpl is not None
            assert tpl.version == "1.0"
            assert tpl.is_active is True
            sections = tpl.sections.all()
            assert len(sections) == 1
            criteria = sections[0].criteria.all()
            assert len(criteria) == 1
            assert criteria[0].code == "C1"
            anchors = criteria[0].scoring_anchors.all()
            assert len(anchors) == 2

    def test_create_template_missing_name_returns_400(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
        client.set_cookie("session_token", token)
        resp = client.post(
            "/admin/templates/new",
            data={"name": "", "version": "1.0"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Template editing — in-place (no audits)
# ---------------------------------------------------------------------------


class TestTemplateEditInPlace:
    def test_edit_template_no_audits(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
            tpl = _create_template(db.session, name="Original")
            tpl_id = tpl.id
        client.set_cookie("session_token", token)
        resp = client.post(
            f"/admin/templates/{tpl_id}",
            data={
                "name": "Updated",
                "version": "1.1",
                "description": "Updated desc",
                "section_0_name": "New Section",
                "section_0_criterion_0_code": "U1",
                "section_0_criterion_0_title": "Updated Criterion",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            tpl = db.session.get(AuditTemplate, tpl_id)
            assert tpl.name == "Updated"
            assert tpl.version == "1.1"
            sections = tpl.sections.all()
            assert len(sections) == 1
            assert sections[0].name == "New Section"

    def test_edit_nonexistent_template_redirects(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
        client.set_cookie("session_token", token)
        resp = client.get("/admin/templates/9999")
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Tests: Template editing — versioning (audits exist)
# ---------------------------------------------------------------------------


class TestTemplateVersioning:
    def test_edit_template_with_audits_creates_new_version(self, app, client):
        """Editing a template that has audits should create a new version,
        leaving the original intact for existing audits (Req 3.3)."""
        with app.app_context():
            _, token = _create_admin(db.session)
            admin = User.query.filter_by(username="admin_tpl").first()
            tpl = _create_template(db.session, name="Versioned", version="1.0")
            tpl_id = tpl.id

            # Create an audit referencing this template
            audit = Audit(
                template_id=tpl.id,
                auditor_id=admin.id,
                status="Draft",
            )
            db.session.add(audit)
            db.session.commit()
            audit_id = audit.id

        client.set_cookie("session_token", token)
        resp = client.post(
            f"/admin/templates/{tpl_id}",
            data={
                "name": "Versioned",
                "version": "2.0",
                "section_0_name": "New Section",
                "section_0_criterion_0_code": "V1",
                "section_0_criterion_0_title": "New Criterion",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            # Original template should still exist and be deactivated
            original = db.session.get(AuditTemplate, tpl_id)
            assert original is not None
            assert original.is_active is False

            # Audit still references the original template
            audit = db.session.get(Audit, audit_id)
            assert audit.template_id == tpl_id

            # New version should exist
            new_tpl = AuditTemplate.query.filter_by(
                name="Versioned", version="2.0"
            ).first()
            assert new_tpl is not None
            assert new_tpl.is_active is True
            assert new_tpl.id != tpl_id

    def test_edit_template_with_audits_auto_increments_version(self, app, client):
        """If no version is provided, it should auto-increment."""
        with app.app_context():
            _, token = _create_admin(db.session)
            admin = User.query.filter_by(username="admin_tpl").first()
            tpl = _create_template(db.session, name="AutoVer", version="3.0")
            tpl_id = tpl.id

            audit = Audit(
                template_id=tpl.id,
                auditor_id=admin.id,
                status="Draft",
            )
            db.session.add(audit)
            db.session.commit()

        client.set_cookie("session_token", token)
        resp = client.post(
            f"/admin/templates/{tpl_id}",
            data={
                "name": "AutoVer",
                "version": "",  # empty → auto-increment
                "section_0_name": "S1",
                "section_0_criterion_0_code": "A1",
                "section_0_criterion_0_title": "Auto",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            new_tpl = AuditTemplate.query.filter(
                AuditTemplate.name == "AutoVer",
                AuditTemplate.id != tpl_id,
            ).first()
            assert new_tpl is not None
            assert new_tpl.version == "4.0"


# ---------------------------------------------------------------------------
# Tests: Active/inactive toggle
# ---------------------------------------------------------------------------


class TestTemplateToggle:
    def test_toggle_active_to_inactive(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
            tpl = _create_template(db.session, is_active=True)
            tpl_id = tpl.id
        client.set_cookie("session_token", token)
        resp = client.post(f"/admin/templates/{tpl_id}/toggle", follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            tpl = db.session.get(AuditTemplate, tpl_id)
            assert tpl.is_active is False

    def test_toggle_inactive_to_active(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
            tpl = _create_template(db.session, is_active=False)
            tpl_id = tpl.id
        client.set_cookie("session_token", token)
        resp = client.post(f"/admin/templates/{tpl_id}/toggle", follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            tpl = db.session.get(AuditTemplate, tpl_id)
            assert tpl.is_active is True

    def test_toggle_nonexistent_template_redirects(self, app, client):
        with app.app_context():
            _, token = _create_admin(db.session)
        client.set_cookie("session_token", token)
        resp = client.post("/admin/templates/9999/toggle", follow_redirects=False)
        assert resp.status_code == 302
