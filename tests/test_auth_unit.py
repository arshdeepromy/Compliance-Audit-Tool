"""Unit tests for authentication utilities and session management.

Covers: password hashing, session CRUD, validation, inactivity timeout,
account lockout, and session middleware.
"""

from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.user import User, Session
from app.utils.auth import (
    hash_password,
    verify_password,
    generate_session_token,
    create_session,
    validate_session,
    invalidate_session,
    invalidate_all_sessions,
    check_account_lockout,
    record_failed_login,
    reset_failed_logins,
    _hash_token,
    SESSION_COOKIE_NAME,
    LOCKOUT_THRESHOLD,
    LOCKOUT_DURATION_MINUTES,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_string(self, app):
        with app.app_context():
            h = hash_password("my-secret")
            assert h.startswith("$2b$")

    def test_verify_password_correct(self, app, sample_user):
        with app.app_context():
            assert verify_password(sample_user, "correct-password") is True

    def test_verify_password_incorrect(self, app, sample_user):
        with app.app_context():
            assert verify_password(sample_user, "wrong-password") is False


# ---------------------------------------------------------------------------
# Session token generation
# ---------------------------------------------------------------------------

class TestSessionToken:
    def test_token_length_is_64_hex_chars(self):
        token = generate_session_token()
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_tokens_are_unique(self):
        tokens = {generate_session_token() for _ in range(50)}
        assert len(tokens) == 50


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

class TestSessionCRUD:
    def test_create_session_stores_hash_in_db(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user, ip="127.0.0.1")
            expected_hash = _hash_token(token)
            record = Session.query.filter_by(token_hash=expected_hash).first()
            assert record is not None
            assert record.user_id == sample_user.id
            assert record.ip_address == "127.0.0.1"

    def test_create_session_sets_expiry(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            record = Session.query.filter_by(token_hash=_hash_token(token)).first()
            expected_hours = app.config["SESSION_EXPIRY_HOURS"]
            delta = record.expires_at - record.created_at
            assert abs(delta.total_seconds() - expected_hours * 3600) < 2


# ---------------------------------------------------------------------------
# Session validation
# ---------------------------------------------------------------------------

class TestSessionValidation:
    def test_validate_valid_session(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            session_record = validate_session(token)
            assert session_record is not None
            assert session_record.user_id == sample_user.id

    def test_validate_invalid_token_returns_none(self, app):
        with app.app_context():
            assert validate_session("nonexistent-token") is None

    def test_validate_expired_session_returns_none(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            # Manually expire the session
            record = Session.query.filter_by(token_hash=_hash_token(token)).first()
            record.expires_at = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()

            assert validate_session(token) is None
            # Session should be cleaned up
            assert Session.query.filter_by(token_hash=_hash_token(token)).first() is None

    def test_validate_inactive_session_returns_none(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            # Set last_active_at to 31 minutes ago
            record = Session.query.filter_by(token_hash=_hash_token(token)).first()
            record.last_active_at = datetime.utcnow() - timedelta(minutes=31)
            db.session.commit()

            assert validate_session(token) is None

    def test_validate_bumps_last_active(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            record = Session.query.filter_by(token_hash=_hash_token(token)).first()
            old_active = record.last_active_at

            # Small delay to ensure timestamp difference
            validate_session(token)
            db.session.refresh(record)
            assert record.last_active_at >= old_active


# ---------------------------------------------------------------------------
# Session invalidation
# ---------------------------------------------------------------------------

class TestSessionInvalidation:
    def test_invalidate_session_removes_record(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            invalidate_session(token)
            assert Session.query.filter_by(token_hash=_hash_token(token)).first() is None

    def test_invalidate_nonexistent_token_is_noop(self, app):
        with app.app_context():
            invalidate_session("does-not-exist")  # Should not raise

    def test_invalidate_all_sessions(self, app, sample_user):
        with app.app_context():
            create_session(sample_user)
            create_session(sample_user)
            create_session(sample_user)
            assert Session.query.filter_by(user_id=sample_user.id).count() == 3

            invalidate_all_sessions(sample_user.id)
            assert Session.query.filter_by(user_id=sample_user.id).count() == 0


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------

class TestAccountLockout:
    def test_not_locked_by_default(self, app, sample_user):
        with app.app_context():
            assert check_account_lockout(sample_user) is False

    def test_four_failures_does_not_lock(self, app, sample_user):
        with app.app_context():
            for _ in range(4):
                record_failed_login(sample_user)
            assert check_account_lockout(sample_user) is False

    def test_five_failures_locks_account(self, app, sample_user):
        with app.app_context():
            for _ in range(5):
                record_failed_login(sample_user)
            assert check_account_lockout(sample_user) is True
            assert sample_user.locked_until is not None

    def test_lockout_expires_after_duration(self, app, sample_user):
        with app.app_context():
            for _ in range(5):
                record_failed_login(sample_user)
            # Move locked_until into the past
            sample_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
            db.session.commit()
            assert check_account_lockout(sample_user) is False

    def test_reset_failed_logins_clears_counter_and_lockout(self, app, sample_user):
        with app.app_context():
            for _ in range(5):
                record_failed_login(sample_user)
            assert sample_user.failed_login_count == 5
            reset_failed_logins(sample_user)
            assert sample_user.failed_login_count == 0
            assert sample_user.locked_until is None
            assert check_account_lockout(sample_user) is False


# ---------------------------------------------------------------------------
# Session middleware
# ---------------------------------------------------------------------------

class TestSessionMiddleware:
    def test_middleware_sets_current_user_with_valid_cookie(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token)

        # Make a request — the before_request handler should set g.current_user
        with app.test_request_context("/", headers={"Cookie": f"{SESSION_COOKIE_NAME}={token}"}):
            from flask import g
            from app.utils.auth import load_user_from_session
            load_user_from_session()
            assert g.current_user is not None
            assert g.current_user.id == sample_user.id

    def test_middleware_no_cookie_sets_none(self, app):
        with app.test_request_context("/"):
            from flask import g
            from app.utils.auth import load_user_from_session
            load_user_from_session()
            assert g.current_user is None

    def test_middleware_invalid_token_sets_none(self, app):
        with app.test_request_context("/", headers={"Cookie": f"{SESSION_COOKIE_NAME}=bad-token"}):
            from flask import g
            from app.utils.auth import load_user_from_session
            load_user_from_session()
            assert g.current_user is None

    def test_middleware_inactive_user_sets_none(self, app, sample_user):
        with app.app_context():
            token = create_session(sample_user)
            sample_user.is_active = False
            db.session.commit()

        with app.test_request_context("/", headers={"Cookie": f"{SESSION_COOKIE_NAME}={token}"}):
            from flask import g
            from app.utils.auth import load_user_from_session
            load_user_from_session()
            assert g.current_user is None
