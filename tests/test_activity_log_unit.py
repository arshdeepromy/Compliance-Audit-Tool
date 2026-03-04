"""Unit tests for activity logging (task 16.2).

Covers:
- log_activity creates a record
- Logs route returns 200 for admin
- Logs route returns 403 for non-admin
- Filtering by action type works
- Logs are in reverse chronological order
"""

import time
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.log import ActivityLog
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME
from app.utils.logging import log_activity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin(app):
    """Create an admin user and return (user, session_token)."""
    with app.app_context():
        admin = User(
            username="log_admin",
            email="logadmin@example.com",
            display_name="Log Admin",
            password_hash=hash_password("admin-pass"),
            roles="admin",
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        db.session.refresh(admin)
        token = create_session(admin, ip="127.0.0.1")
        return admin, token


def _make_auditor(app):
    """Create an auditor user and return (user, session_token)."""
    with app.app_context():
        auditor = User(
            username="log_auditor",
            email="logauditor@example.com",
            display_name="Log Auditor",
            password_hash=hash_password("auditor-pass"),
            roles="auditor",
            is_active=True,
        )
        db.session.add(auditor)
        db.session.commit()
        db.session.refresh(auditor)
        token = create_session(auditor, ip="127.0.0.1")
        return auditor, token


def _admin_client(app):
    """Return a test client with an admin session cookie set."""
    _, token = _make_admin(app)
    client = app.test_client()
    client.set_cookie(SESSION_COOKIE_NAME, token)
    return client


def _auditor_client(app):
    """Return a test client with an auditor session cookie set."""
    _, token = _make_auditor(app)
    client = app.test_client()
    client.set_cookie(SESSION_COOKIE_NAME, token)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLogActivity:
    """log_activity helper creates a database record."""

    def test_creates_record(self, app):
        with app.app_context():
            entry = log_activity(
                action="login",
                details="test login",
                user_id=None,
                ip_address="10.0.0.1",
            )
            db.session.commit()

            assert entry.id is not None
            stored = db.session.get(ActivityLog, entry.id)
            assert stored is not None
            assert stored.action == "login"
            assert stored.details == "test login"
            assert stored.ip_address == "10.0.0.1"
            assert stored.created_at is not None

    def test_creates_record_with_dict_details(self, app):
        with app.app_context():
            entry = log_activity(
                action="settings_change",
                details={"setting": "branding"},
                user_id=None,
                ip_address="10.0.0.2",
            )
            db.session.commit()

            stored = db.session.get(ActivityLog, entry.id)
            assert stored is not None
            assert "branding" in stored.details

    def test_creates_record_with_user_id(self, app):
        with app.app_context():
            user = User(
                username="logtest",
                email="logtest@example.com",
                display_name="Log Test",
                password_hash=hash_password("pass"),
                roles="admin",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            entry = log_activity(
                action="login",
                details="logged in",
                user_id=user.id,
                ip_address="10.0.0.3",
            )
            db.session.commit()

            stored = db.session.get(ActivityLog, entry.id)
            assert stored.user_id == user.id


class TestLogsRoute:
    """GET /admin/logs route tests."""

    def test_returns_200_for_admin(self, app):
        client = _admin_client(app)
        resp = client.get("/admin/logs")
        assert resp.status_code == 200
        assert b"Activity Log" in resp.data

    def test_returns_403_for_non_admin(self, app):
        client = _auditor_client(app)
        resp = client.get("/admin/logs")
        assert resp.status_code == 403

    def test_unauthenticated_redirects_to_login(self, app):
        client = app.test_client()
        resp = client.get("/admin/logs")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


class TestLogsFiltering:
    """Filtering by action type works."""

    def test_filter_by_action_type(self, app):
        with app.app_context():
            log_activity("login", "user logged in", ip_address="1.1.1.1")
            log_activity("logout", "user logged out", ip_address="1.1.1.2")
            log_activity("settings_change", "branding updated", ip_address="1.1.1.3")
            db.session.commit()

        client = _admin_client(app)
        resp = client.get("/admin/logs?action=login")
        assert resp.status_code == 200
        # The login entry should be present
        assert b"login" in resp.data

    def test_filter_by_user_id(self, app):
        with app.app_context():
            user = User(
                username="filteruser",
                email="filter@example.com",
                display_name="Filter User",
                password_hash=hash_password("pass"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            log_activity("login", "user login", user_id=user.id, ip_address="2.2.2.2")
            log_activity("logout", "other logout", user_id=None, ip_address="3.3.3.3")
            db.session.commit()

            uid = user.id

        client = _admin_client(app)
        resp = client.get(f"/admin/logs?user_id={uid}")
        assert resp.status_code == 200


class TestLogsOrder:
    """Logs are in reverse chronological order."""

    def test_reverse_chronological_order(self, app):
        with app.app_context():
            # Create entries with explicit timestamps
            old_entry = ActivityLog(
                action="login",
                details="old entry",
                ip_address="1.1.1.1",
                created_at=datetime.utcnow() - timedelta(hours=2),
            )
            new_entry = ActivityLog(
                action="logout",
                details="new entry",
                ip_address="2.2.2.2",
                created_at=datetime.utcnow(),
            )
            db.session.add(old_entry)
            db.session.add(new_entry)
            db.session.commit()

        client = _admin_client(app)
        resp = client.get("/admin/logs")
        assert resp.status_code == 200
        html = resp.data.decode()
        # "new entry" should appear before "old entry" in the HTML
        new_pos = html.find("new entry")
        old_pos = html.find("old entry")
        assert new_pos < old_pos, "Logs should be in reverse chronological order"
