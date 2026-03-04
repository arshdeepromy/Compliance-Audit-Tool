"""Unit tests for RBAC decorators and utilities."""

import pytest
from flask import Blueprint, Flask, g

from app.utils.rbac import (
    _parse_roles,
    has_any_role,
    has_role,
    login_required,
    roles_required,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME
from app.extensions import db
from app.config import TestConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_user(roles: str, username: str = "testuser") -> User:
    """Create a User instance with the given roles."""
    return User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        password_hash=hash_password("password123"),
        roles=roles,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# _parse_roles
# ---------------------------------------------------------------------------


class TestParseRoles:
    def test_single_role(self):
        assert _parse_roles("admin") == {"admin"}

    def test_multiple_roles(self):
        assert _parse_roles("admin,auditor") == {"admin", "auditor"}

    def test_whitespace_handling(self):
        assert _parse_roles(" admin , auditor ") == {"admin", "auditor"}

    def test_case_insensitive(self):
        assert _parse_roles("Admin,AUDITOR") == {"admin", "auditor"}

    def test_empty_string(self):
        assert _parse_roles("") == set()

    def test_trailing_comma(self):
        assert _parse_roles("admin,") == {"admin"}


# ---------------------------------------------------------------------------
# has_role / has_any_role
# ---------------------------------------------------------------------------


class TestHasRole:
    def test_user_has_role(self):
        user = _make_user("auditor")
        assert has_role(user, "auditor") is True

    def test_user_lacks_role(self):
        user = _make_user("viewer")
        assert has_role(user, "admin") is False

    def test_none_user(self):
        assert has_role(None, "admin") is False

    def test_case_insensitive(self):
        user = _make_user("Admin")
        assert has_role(user, "admin") is True


class TestHasAnyRole:
    def test_user_has_one_of_roles(self):
        user = _make_user("auditor")
        assert has_any_role(user, "admin", "auditor") is True

    def test_user_has_none_of_roles(self):
        user = _make_user("viewer")
        assert has_any_role(user, "admin", "auditor") is False

    def test_none_user(self):
        assert has_any_role(None, "admin") is False

    def test_multi_role_user(self):
        user = _make_user("auditor,auditee")
        assert has_any_role(user, "auditee") is True


# ---------------------------------------------------------------------------
# Decorator integration tests — use a fresh app per test class
# ---------------------------------------------------------------------------


def _create_rbac_test_app(tmp_path):
    """Create a fresh Flask app with test routes for RBAC decorator testing."""

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'rbac_test.db'}"

    from app import create_app

    app = create_app(config_class=LocalTestConfig, run_startup=False)

    # Register a test blueprint with protected routes BEFORE first request
    test_bp = Blueprint("rbac_test", __name__)

    @test_bp.route("/test-login-required")
    @login_required
    def login_required_view():
        return "OK"

    @test_bp.route("/test-admin-only")
    @roles_required("admin")
    def admin_only():
        return "admin"

    @test_bp.route("/test-auditor-only")
    @roles_required("auditor")
    def auditor_only():
        return "auditor"

    @test_bp.route("/test-multi-role")
    @roles_required("auditor", "auditee")
    def multi_role():
        return "ok"

    app.register_blueprint(test_bp)

    with app.app_context():
        db.create_all()

    return app


# ---------------------------------------------------------------------------
# login_required decorator
# ---------------------------------------------------------------------------


class TestLoginRequired:
    def test_unauthenticated_redirects_to_login(self, tmp_path):
        """Unauthenticated request should redirect to login."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()
        resp = client.get("/test-login-required")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_authenticated_user_passes(self, tmp_path):
        """Authenticated user should access the endpoint."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("viewer", username="logintest")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-login-required")
        assert resp.status_code == 200
        assert resp.data == b"OK"


# ---------------------------------------------------------------------------
# roles_required decorator
# ---------------------------------------------------------------------------


class TestRolesRequired:
    def test_unauthenticated_redirects(self, tmp_path):
        """Unauthenticated request should redirect to login."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()
        resp = client.get("/test-admin-only")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_correct_role_passes(self, tmp_path):
        """User with the required role should access the endpoint."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("auditor", username="rolepass")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-auditor-only")
        assert resp.status_code == 200
        assert resp.data == b"auditor"

    def test_wrong_role_returns_403(self, tmp_path):
        """User without the required role should get 403."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("viewer", username="role403")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-auditor-only")
        assert resp.status_code == 403

    def test_admin_has_full_access(self, tmp_path):
        """Admin should access any endpoint regardless of required roles (Req 2.6)."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("admin", username="adminfull")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-auditor-only")
        assert resp.status_code == 200

    def test_multiple_roles_any_matches(self, tmp_path):
        """User with any of the listed roles should pass."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("auditee", username="multirole")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-multi-role")
        assert resp.status_code == 200

    def test_viewer_cannot_access_auditor_endpoint(self, tmp_path):
        """Viewer should not access auditor-only endpoints (Req 2.5 vs 2.3)."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("viewer", username="viewerblocked")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-auditor-only")
        assert resp.status_code == 403

    def test_multi_role_user_with_admin(self, tmp_path):
        """User with admin among multiple roles should have full access."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("viewer,admin", username="multiadmin")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-auditor-only")
        assert resp.status_code == 200

    def test_auditee_cannot_access_admin_endpoint(self, tmp_path):
        """Auditee should not access admin-only endpoints (Req 2.7)."""
        app = _create_rbac_test_app(tmp_path)
        client = app.test_client()

        with app.app_context():
            user = _make_user("auditee", username="auditeeblocked")
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            token = create_session(user, ip="127.0.0.1")

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.get("/test-admin-only")
        assert resp.status_code == 403
