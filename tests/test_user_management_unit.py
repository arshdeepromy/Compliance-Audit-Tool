"""Unit tests for user management (admin panel).

Covers:
- User list displays all users
- Create user with valid data
- Create user with missing required fields returns 400
- Create user with duplicate username returns 400
- Edit user updates fields
- Deactivate user sets is_active=False
- RBAC: non-admin gets 403
"""

import pytest

from app.extensions import db
from app.models.user import User, Session
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin(app):
    """Create an admin user and return (user, session_token)."""
    with app.app_context():
        admin = User(
            username="admin_user",
            email="admin@example.com",
            display_name="Admin",
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
            username="auditor_user",
            email="auditor@example.com",
            display_name="Auditor",
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
# User list
# ---------------------------------------------------------------------------


class TestUserList:
    def test_user_list_displays_all_users(self, app):
        client = _admin_client(app)
        # The admin user already exists from _admin_client
        with app.app_context():
            u2 = User(
                username="second_user",
                email="second@example.com",
                display_name="Second",
                password_hash=hash_password("pass"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(u2)
            db.session.commit()

        resp = client.get("/admin/users")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "admin_user" in html
        assert "second_user" in html

    def test_user_list_shows_roles_and_status(self, app):
        client = _admin_client(app)
        resp = client.get("/admin/users")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "admin" in html
        assert "Yes" in html  # is_active


# ---------------------------------------------------------------------------
# Create user
# ---------------------------------------------------------------------------


class TestCreateUser:
    def test_create_user_get_returns_form(self, app):
        client = _admin_client(app)
        resp = client.get("/admin/users/new")
        assert resp.status_code == 200
        assert b"Create User" in resp.data

    def test_create_user_with_valid_data(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "newuser",
                "email": "new@example.com",
                "display_name": "New User",
                "password": "secure-pass-123",
                "roles": "auditor",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302  # redirect to user list

        with app.app_context():
            user = User.query.filter_by(username="newuser").first()
            assert user is not None
            assert user.email == "new@example.com"
            assert user.display_name == "New User"
            assert "auditor" in user.roles
            assert user.is_active is True

    def test_create_user_with_multiple_roles(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "multirole",
                "email": "multi@example.com",
                "display_name": "Multi Role",
                "password": "pass123",
                "roles": ["admin", "auditor"],
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            user = User.query.filter_by(username="multirole").first()
            assert user is not None
            assert "admin" in user.roles
            assert "auditor" in user.roles

    def test_create_user_missing_username_returns_400(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "",
                "email": "no-user@example.com",
                "display_name": "No Username",
                "password": "pass123",
                "roles": "auditor",
            },
        )
        assert resp.status_code == 400

    def test_create_user_missing_password_returns_400(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "nopass",
                "email": "nopass@example.com",
                "display_name": "No Pass",
                "password": "",
                "roles": "auditor",
            },
        )
        assert resp.status_code == 400

    def test_create_user_missing_email_returns_400(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "noemail",
                "email": "",
                "display_name": "No Email",
                "password": "pass123",
                "roles": "auditor",
            },
        )
        assert resp.status_code == 400

    def test_create_user_missing_display_name_returns_400(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "noname",
                "email": "noname@example.com",
                "display_name": "",
                "password": "pass123",
                "roles": "auditor",
            },
        )
        assert resp.status_code == 400

    def test_create_user_missing_roles_returns_400(self, app):
        client = _admin_client(app)
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "norole",
                "email": "norole@example.com",
                "display_name": "No Role",
                "password": "pass123",
            },
        )
        assert resp.status_code == 400

    def test_create_user_duplicate_username_returns_400(self, app):
        client = _admin_client(app)
        # admin_user already exists
        resp = client.post(
            "/admin/users/new",
            data={
                "username": "admin_user",
                "email": "dup@example.com",
                "display_name": "Duplicate",
                "password": "pass123",
                "roles": "auditor",
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Edit user
# ---------------------------------------------------------------------------


class TestEditUser:
    def test_edit_user_get_returns_form(self, app):
        client = _admin_client(app)
        with app.app_context():
            admin = User.query.filter_by(username="admin_user").first()
            uid = admin.id

        resp = client.get(f"/admin/users/{uid}")
        assert resp.status_code == 200
        assert b"Edit User" in resp.data

    def test_edit_user_updates_fields(self, app):
        client = _admin_client(app)
        with app.app_context():
            target = User(
                username="editable",
                email="edit@example.com",
                display_name="Old Name",
                password_hash=hash_password("pass"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(target)
            db.session.commit()
            db.session.refresh(target)
            uid = target.id

        resp = client.post(
            f"/admin/users/{uid}",
            data={
                "action": "save",
                "display_name": "New Name",
                "email": "newedit@example.com",
                "roles": ["auditor", "viewer"],
                "mfa_type": "totp",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            user = db.session.get(User, uid)
            assert user.display_name == "New Name"
            assert user.email == "newedit@example.com"
            assert "auditor" in user.roles
            assert "viewer" in user.roles
            assert user.mfa_type == "totp"

    def test_edit_nonexistent_user_redirects(self, app):
        client = _admin_client(app)
        resp = client.get("/admin/users/99999", follow_redirects=False)
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Deactivate user
# ---------------------------------------------------------------------------


class TestDeactivateUser:
    def test_deactivate_user_sets_inactive(self, app):
        client = _admin_client(app)
        with app.app_context():
            target = User(
                username="deactivatable",
                email="deact@example.com",
                display_name="Deact User",
                password_hash=hash_password("pass"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(target)
            db.session.commit()
            db.session.refresh(target)
            uid = target.id
            # Create a session for this user
            create_session(target, ip="10.0.0.1")
            assert Session.query.filter_by(user_id=uid).count() == 1

        resp = client.post(
            f"/admin/users/{uid}",
            data={
                "action": "deactivate",
                "display_name": "Deact User",
                "email": "deact@example.com",
                "roles": "auditor",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            user = db.session.get(User, uid)
            assert user.is_active is False
            # Sessions should be invalidated
            assert Session.query.filter_by(user_id=uid).count() == 0

    def test_activate_user(self, app):
        client = _admin_client(app)
        with app.app_context():
            target = User(
                username="inactive_user",
                email="inactive@example.com",
                display_name="Inactive",
                password_hash=hash_password("pass"),
                roles="viewer",
                is_active=False,
            )
            db.session.add(target)
            db.session.commit()
            db.session.refresh(target)
            uid = target.id

        resp = client.post(
            f"/admin/users/{uid}",
            data={
                "action": "activate",
                "display_name": "Inactive",
                "email": "inactive@example.com",
                "roles": "viewer",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            user = db.session.get(User, uid)
            assert user.is_active is True


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------


class TestResetPassword:
    def test_reset_password_changes_hash(self, app):
        client = _admin_client(app)
        with app.app_context():
            target = User(
                username="resetme",
                email="reset@example.com",
                display_name="Reset Me",
                password_hash=hash_password("old-pass"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(target)
            db.session.commit()
            db.session.refresh(target)
            uid = target.id
            old_hash = target.password_hash

        resp = client.post(
            f"/admin/users/{uid}",
            data={
                "action": "reset_password",
                "display_name": "Reset Me",
                "email": "reset@example.com",
                "roles": "auditor",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            user = db.session.get(User, uid)
            assert user.password_hash != old_hash


# ---------------------------------------------------------------------------
# RBAC: non-admin gets 403
# ---------------------------------------------------------------------------


class TestUserManagementRBAC:
    def test_auditor_cannot_access_user_list(self, app):
        client = _auditor_client(app)
        resp = client.get("/admin/users")
        assert resp.status_code == 403

    def test_auditor_cannot_create_user(self, app):
        client = _auditor_client(app)
        resp = client.get("/admin/users/new")
        assert resp.status_code == 403

    def test_auditor_cannot_edit_user(self, app):
        client = _auditor_client(app)
        resp = client.get("/admin/users/1")
        assert resp.status_code == 403

    def test_unauthenticated_redirects_to_login(self, app):
        client = app.test_client()
        resp = client.get("/admin/users", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")
