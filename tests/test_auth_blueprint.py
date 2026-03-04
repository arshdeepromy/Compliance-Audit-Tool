"""Unit tests for the auth blueprint: login, logout, MFA, password reset routes."""

from datetime import datetime, timedelta

import pyotp
import pytest

from app.extensions import db
from app.models.user import User, Session
from app.utils.auth import (
    SESSION_COOKIE_NAME,
    create_session,
    hash_password,
    _hash_token,
)


def _get_cookie(response, name):
    """Extract a cookie value from a response's Set-Cookie headers."""
    for header_val in response.headers.getlist("Set-Cookie"):
        if header_val.startswith(f"{name}="):
            value = header_val.split("=", 1)[1].split(";")[0]
            return value
    return None


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_get_login_returns_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_valid_login_sets_session_cookie(self, app, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        cookie_val = _get_cookie(resp, SESSION_COOKIE_NAME)
        assert cookie_val is not None
        assert len(cookie_val) == 64  # 256-bit hex token

    def test_session_cookie_is_httponly(self, app, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
            follow_redirects=False,
        )
        set_cookie = next(
            (h for h in resp.headers.getlist("Set-Cookie") if SESSION_COOKIE_NAME in h),
            "",
        )
        assert "HttpOnly" in set_cookie

    def test_session_cookie_samesite_lax(self, app, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
            follow_redirects=False,
        )
        set_cookie = next(
            (h for h in resp.headers.getlist("Set-Cookie") if SESSION_COOKIE_NAME in h),
            "",
        )
        assert "SameSite=Lax" in set_cookie

    def test_valid_login_creates_session_in_db(self, app, client, sample_user):
        client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
        )
        with app.app_context():
            sessions = Session.query.filter_by(user_id=sample_user.id).all()
            assert len(sessions) == 1

    def test_invalid_username_returns_401(self, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "nonexistent", "password": "whatever"},
        )
        assert resp.status_code == 401

    def test_invalid_password_returns_401(self, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    def test_uniform_error_message_wrong_username(self, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "nonexistent", "password": "whatever"},
        )
        assert b"Invalid username or password" in resp.data

    def test_uniform_error_message_wrong_password(self, client, sample_user):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrong-password"},
        )
        assert b"Invalid username or password" in resp.data

    def test_locked_account_returns_403(self, app, client, sample_user):
        # Modify user via the test client's implicit app context
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrong"},
        )
        # Lock the account directly
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            user.failed_login_count = 5
            user.locked_until = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()

        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
        )
        assert resp.status_code == 403
        assert b"Account temporarily locked" in resp.data

    def test_inactive_user_returns_401(self, app, client):
        with app.app_context():
            user = User(
                username="inactiveuser",
                email="inactive@example.com",
                display_name="Inactive User",
                password_hash=hash_password("correct-password"),
                roles="auditor",
                is_active=False,
            )
            db.session.add(user)
            db.session.commit()

        resp = client.post(
            "/login",
            data={"username": "inactiveuser", "password": "correct-password"},
        )
        assert resp.status_code == 401

    def test_failed_login_increments_counter(self, app, client, sample_user):
        client.post(
            "/login",
            data={"username": "testuser", "password": "wrong"},
        )
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            assert user.failed_login_count == 1

    def test_successful_login_resets_failed_counter(self, app, client):
        with app.app_context():
            user = User(
                username="faileduser",
                email="failed@example.com",
                display_name="Failed User",
                password_hash=hash_password("correct-password"),
                roles="auditor",
                is_active=True,
                failed_login_count=3,
            )
            db.session.add(user)
            db.session.commit()

        client.post(
            "/login",
            data={"username": "faileduser", "password": "correct-password"},
        )
        with app.app_context():
            user = User.query.filter_by(username="faileduser").first()
            assert user.failed_login_count == 0


# ---------------------------------------------------------------------------
# MFA — TOTP
# ---------------------------------------------------------------------------


class TestMFATotp:
    @pytest.fixture
    def totp_user(self, app):
        """Create a user with TOTP MFA enabled."""
        with app.app_context():
            secret = pyotp.random_base32()
            user = User(
                username="totpuser",
                email="totp@example.com",
                display_name="TOTP User",
                password_hash=hash_password("totp-password"),
                roles="auditor",
                is_active=True,
                mfa_type="totp",
                totp_secret=secret,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            yield user

    def test_login_with_mfa_redirects_to_mfa_page(self, client, totp_user):
        resp = client.post(
            "/login",
            data={"username": "totpuser", "password": "totp-password"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login/mfa" in resp.headers["Location"]

    def test_login_with_mfa_does_not_issue_session_cookie(self, client, totp_user):
        resp = client.post(
            "/login",
            data={"username": "totpuser", "password": "totp-password"},
            follow_redirects=False,
        )
        cookie_val = _get_cookie(resp, SESSION_COOKIE_NAME)
        assert cookie_val is None

    def test_valid_totp_code_issues_session(self, app, client, totp_user):
        # Step 1: login with password
        client.post(
            "/login",
            data={"username": "totpuser", "password": "totp-password"},
        )
        # Step 2: submit valid TOTP code
        with app.app_context():
            user = db.session.get(User, totp_user.id)
            totp = pyotp.TOTP(user.totp_secret)
            code = totp.now()

        resp = client.post(
            "/login/mfa",
            data={"code": code},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        cookie_val = _get_cookie(resp, SESSION_COOKIE_NAME)
        assert cookie_val is not None

    def test_invalid_totp_code_returns_401(self, client, totp_user):
        client.post(
            "/login",
            data={"username": "totpuser", "password": "totp-password"},
        )
        resp = client.post(
            "/login/mfa",
            data={"code": "000000"},
        )
        assert resp.status_code == 401
        assert b"Invalid verification code" in resp.data

    def test_mfa_page_without_session_redirects_to_login(self, client):
        resp = client.get("/login/mfa", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# MFA — Email
# ---------------------------------------------------------------------------


class TestMFAEmail:
    @pytest.fixture
    def email_mfa_user(self, app):
        """Create a user with email MFA enabled."""
        with app.app_context():
            user = User(
                username="emailmfa",
                email="emailmfa@example.com",
                display_name="Email MFA User",
                password_hash=hash_password("email-password"),
                roles="auditor",
                is_active=True,
                mfa_type="email",
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            yield user

    def test_email_mfa_login_redirects_to_mfa(self, client, email_mfa_user):
        resp = client.post(
            "/login",
            data={"username": "emailmfa", "password": "email-password"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login/mfa" in resp.headers["Location"]

    def test_valid_email_code_issues_session(self, app, client, email_mfa_user):
        # Login to trigger email MFA
        client.post(
            "/login",
            data={"username": "emailmfa", "password": "email-password"},
        )
        # Get the code from the Flask session
        with client.session_transaction() as sess:
            code = sess.get("mfa_email_code")
            assert code is not None

        resp = client.post(
            "/login/mfa",
            data={"code": code},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        cookie_val = _get_cookie(resp, SESSION_COOKIE_NAME)
        assert cookie_val is not None

    def test_invalid_email_code_returns_401(self, client, email_mfa_user):
        client.post(
            "/login",
            data={"username": "emailmfa", "password": "email-password"},
        )
        resp = client.post(
            "/login/mfa",
            data={"code": "999999"},
        )
        assert resp.status_code == 401
        assert b"Invalid verification code" in resp.data


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_invalidates_session_in_db(self, app, client, sample_user):
        client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
        )
        with app.app_context():
            assert Session.query.filter_by(user_id=sample_user.id).count() == 1

        client.post("/logout")
        with app.app_context():
            assert Session.query.filter_by(user_id=sample_user.id).count() == 0

    def test_logout_redirects_to_login(self, client, sample_user):
        client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
        )
        resp = client.post("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_logout_deletes_cookie(self, app, client, sample_user):
        client.post(
            "/login",
            data={"username": "testuser", "password": "correct-password"},
        )
        resp = client.post("/logout", follow_redirects=False)
        # The Set-Cookie header should expire/delete the session cookie
        set_cookie = next(
            (h for h in resp.headers.getlist("Set-Cookie") if SESSION_COOKIE_NAME in h),
            "",
        )
        # Flask delete_cookie sets the value to empty and expires in the past
        assert SESSION_COOKIE_NAME in set_cookie


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


class TestPasswordReset:
    def test_get_reset_request_returns_200(self, client):
        resp = client.get("/password/reset")
        assert resp.status_code == 200

    def test_post_reset_request_shows_success_message(self, client, sample_user):
        resp = client.post(
            "/password/reset",
            data={"email": "test@example.com"},
        )
        assert resp.status_code == 200
        assert b"password reset link has been sent" in resp.data

    def test_post_reset_request_nonexistent_email_same_message(self, client):
        resp = client.post(
            "/password/reset",
            data={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert b"password reset link has been sent" in resp.data

    def test_valid_reset_token_shows_form(self, app, client, sample_user):
        from app.blueprints.auth import _generate_password_reset_token

        with app.app_context():
            user = db.session.get(User, sample_user.id)
            token = _generate_password_reset_token(user)

        resp = client.get(f"/password/reset/{token}")
        assert resp.status_code == 200

    def test_invalid_reset_token_redirects(self, client):
        resp = client.get("/password/reset/bad-token", follow_redirects=False)
        assert resp.status_code == 302
        assert "/password/reset" in resp.headers["Location"]

    def test_password_reset_changes_password(self, app, client, sample_user):
        from app.blueprints.auth import _generate_password_reset_token
        from app.utils.auth import verify_password

        with app.app_context():
            user = db.session.get(User, sample_user.id)
            token = _generate_password_reset_token(user)

        resp = client.post(
            f"/password/reset/{token}",
            data={"password": "new-secure-password", "confirm_password": "new-secure-password"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

        # Verify the password was actually changed
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            assert verify_password(user, "new-secure-password") is True

    def test_password_reset_mismatch_returns_400(self, app, client, sample_user):
        from app.blueprints.auth import _generate_password_reset_token

        with app.app_context():
            user = db.session.get(User, sample_user.id)
            token = _generate_password_reset_token(user)

        resp = client.post(
            f"/password/reset/{token}",
            data={"password": "new-password", "confirm_password": "different"},
        )
        assert resp.status_code == 400
        assert b"Passwords do not match" in resp.data

    def test_password_reset_too_short_returns_400(self, app, client, sample_user):
        from app.blueprints.auth import _generate_password_reset_token

        with app.app_context():
            user = db.session.get(User, sample_user.id)
            token = _generate_password_reset_token(user)

        resp = client.post(
            f"/password/reset/{token}",
            data={"password": "short", "confirm_password": "short"},
        )
        assert resp.status_code == 400
        assert b"at least 8 characters" in resp.data
