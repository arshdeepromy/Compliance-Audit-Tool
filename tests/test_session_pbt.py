"""Property-based tests for session management.

Feature: totika-audit-webapp
Property 5: Session invalidation rejects subsequent requests
Property 6: Session tokens are HTTP-only with sufficient entropy

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 1.5, 19.1, 19.2, 19.3, 19.4**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app.extensions import db
from app.models.user import User, Session
from app.utils.auth import (
    SESSION_COOKIE_NAME,
    hash_password,
    create_session,
    validate_session,
    invalidate_session,
    generate_session_token,
    _hash_token,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Inactivity offsets beyond the 30-minute threshold (31–120 minutes)
_inactivity_minutes_st = st.integers(min_value=31, max_value=120)

# Expiry offsets beyond the 8-hour default (9–48 hours)
_expiry_hours_st = st.integers(min_value=9, max_value=48)

# Number of tokens to generate for entropy uniqueness checks
_token_count_st = st.integers(min_value=2, max_value=10)

# Suppress the function-scoped fixture health check
_suppress_fixture_check = settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KNOWN_USERNAME = "session_user"
KNOWN_PASSWORD = "session-correct-pw-456"
KNOWN_EMAIL = "session_user@example.com"


@pytest.fixture(autouse=False)
def session_user(app):
    """Create a known user for session property tests."""
    with app.app_context():
        user = User(
            username=KNOWN_USERNAME,
            email=KNOWN_EMAIL,
            display_name="Session User",
            password_hash=hash_password(KNOWN_PASSWORD),
            roles="auditor",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


def _login_and_get_token(client):
    """Log in with known credentials and return the session token from the cookie."""
    resp = client.post(
        "/login",
        data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    for header_val in resp.headers.getlist("Set-Cookie"):
        if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
            value = header_val.split("=", 1)[1].split(";")[0]
            if value:
                return value
    return None


# ===========================================================================
# Property 5: Session invalidation rejects subsequent requests
# ===========================================================================


class TestProperty5SessionInvalidation:
    """Property 5: Session invalidation rejects subsequent requests.

    *For any* session that has been invalidated (via logout, expiry, or
    inactivity > 30 minutes), all subsequent requests using that session
    token SHALL be rejected.

    **Validates: Requirements 1.5, 19.2, 19.3**
    """

    def test_logout_invalidates_session(self, app, client, session_user):
        """After logout, the session token is rejected by validate_session."""
        token = _login_and_get_token(client)
        assert token is not None

        # Validate the session is active
        with app.app_context():
            session_record = validate_session(token)
            assert session_record is not None

        # Logout via POST
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        client.post("/logout")

        # Session should now be invalid
        with app.app_context():
            session_record = validate_session(token)
            assert session_record is None

    def test_logout_clears_cookie(self, app, client, session_user):
        """Logout response deletes the session cookie."""
        token = _login_and_get_token(client)
        assert token is not None

        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
        resp = client.post("/logout", follow_redirects=False)

        # Check that the cookie is cleared (set to empty or with expires in past)
        found_delete = False
        for header_val in resp.headers.getlist("Set-Cookie"):
            if SESSION_COOKIE_NAME in header_val:
                # Cookie deletion sets value to empty or max_age=0
                if "=" in header_val:
                    val_part = header_val.split("=", 1)[1].split(";")[0]
                    if val_part == "" or "Expires=Thu, 01 Jan 1970" in header_val or "Max-Age=0" in header_val:
                        found_delete = True
        assert found_delete

    @_suppress_fixture_check
    @given(inactivity_minutes=_inactivity_minutes_st)
    def test_inactivity_timeout_invalidates_session(
        self, app, client, session_user, inactivity_minutes
    ):
        """Sessions inactive for > 30 minutes are rejected."""
        with app.app_context():
            user = db.session.get(User, session_user.id)
            token = create_session(user, ip="127.0.0.1")

            # Simulate inactivity by backdating last_active_at
            token_hash = _hash_token(token)
            session_record = Session.query.filter_by(token_hash=token_hash).first()
            assert session_record is not None
            session_record.last_active_at = datetime.utcnow() - timedelta(
                minutes=inactivity_minutes
            )
            db.session.commit()

            # Validation should reject the session
            result = validate_session(token)
            assert result is None

            # Confirm the session record was cleaned up
            remaining = Session.query.filter_by(token_hash=token_hash).first()
            assert remaining is None

    @_suppress_fixture_check
    @given(expiry_hours=_expiry_hours_st)
    def test_expired_session_is_rejected(
        self, app, client, session_user, expiry_hours
    ):
        """Sessions past their absolute expiry are rejected."""
        with app.app_context():
            user = db.session.get(User, session_user.id)
            token = create_session(user, ip="127.0.0.1")

            # Simulate expiry by backdating both created_at and expires_at
            token_hash = _hash_token(token)
            session_record = Session.query.filter_by(token_hash=token_hash).first()
            assert session_record is not None
            past = datetime.utcnow() - timedelta(hours=expiry_hours)
            session_record.created_at = past
            session_record.expires_at = past + timedelta(hours=8)  # 8h default
            session_record.last_active_at = datetime.utcnow()  # recent activity
            db.session.commit()

            # Validation should reject the session
            result = validate_session(token)
            assert result is None

    def test_invalidated_token_reused_is_rejected(self, app, client, session_user):
        """After explicit invalidation, reusing the same token is rejected."""
        with app.app_context():
            user = db.session.get(User, session_user.id)
            token = create_session(user, ip="127.0.0.1")

            # Validate it works first
            assert validate_session(token) is not None

            # Invalidate
            invalidate_session(token)

            # Subsequent validation must fail
            assert validate_session(token) is None

    def test_invalidate_all_sessions_rejects_all_tokens(
        self, app, client, session_user
    ):
        """invalidate_all_sessions kills every session for the user."""
        with app.app_context():
            user = db.session.get(User, session_user.id)
            tokens = [create_session(user, ip="127.0.0.1") for _ in range(3)]

            # All should be valid
            for t in tokens:
                assert validate_session(t) is not None

            # Invalidate all
            from app.utils.auth import invalidate_all_sessions
            invalidate_all_sessions(user.id)

            # All should now be rejected
            for t in tokens:
                assert validate_session(t) is None

    def test_within_inactivity_window_session_is_valid(
        self, app, client, session_user
    ):
        """Sessions within the 30-minute inactivity window remain valid."""
        with app.app_context():
            user = db.session.get(User, session_user.id)
            token = create_session(user, ip="127.0.0.1")

            # Set last_active_at to 25 minutes ago (within 30-min window)
            token_hash = _hash_token(token)
            session_record = Session.query.filter_by(token_hash=token_hash).first()
            session_record.last_active_at = datetime.utcnow() - timedelta(minutes=25)
            db.session.commit()

            # Should still be valid
            result = validate_session(token)
            assert result is not None


# ===========================================================================
# Property 6: Session tokens are HTTP-only with sufficient entropy
# ===========================================================================


class TestProperty6SessionTokenEntropy:
    """Property 6: Session tokens are HTTP-only with sufficient entropy.

    *For any* newly created session, the token SHALL be issued as an
    HTTP-only cookie with the configured expiry, and the token SHALL
    contain at least 256 bits of cryptographically secure random data.

    **Validates: Requirements 19.1, 19.4**
    """

    @_suppress_fixture_check
    @given(data=st.data())
    def test_token_has_minimum_256_bit_entropy(self, app, data):
        """generate_session_token() produces at least 64 hex chars (256 bits)."""
        token = generate_session_token()
        # 256 bits = 32 bytes = 64 hex characters
        assert len(token) >= 64
        # Must be valid hex
        int(token, 16)

    @_suppress_fixture_check
    @given(n=_token_count_st)
    def test_tokens_are_unique(self, app, n):
        """Multiple generated tokens are all distinct (collision resistance)."""
        tokens = [generate_session_token() for _ in range(n)]
        assert len(set(tokens)) == n

    def test_login_sets_httponly_cookie(self, app, client, session_user):
        """Login response sets the session cookie with HttpOnly flag."""
        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        found_httponly = False
        for header_val in resp.headers.getlist("Set-Cookie"):
            if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
                # Check HttpOnly flag is present (case-insensitive)
                if "httponly" in header_val.lower():
                    found_httponly = True
        assert found_httponly, "Session cookie must have HttpOnly flag"

    def test_login_sets_samesite_cookie(self, app, client, session_user):
        """Login response sets the session cookie with SameSite=Lax."""
        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        found_samesite = False
        for header_val in resp.headers.getlist("Set-Cookie"):
            if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
                if "samesite=lax" in header_val.lower():
                    found_samesite = True
        assert found_samesite, "Session cookie must have SameSite=Lax"

    def test_login_sets_max_age_matching_config(self, app, client, session_user):
        """Login response sets max_age matching SESSION_EXPIRY_HOURS config."""
        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        expected_max_age = app.config.get("SESSION_EXPIRY_HOURS", 8) * 3600
        found_max_age = False
        for header_val in resp.headers.getlist("Set-Cookie"):
            if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
                # Parse Max-Age from the cookie header
                for part in header_val.split(";"):
                    part = part.strip()
                    if part.lower().startswith("max-age="):
                        max_age_val = int(part.split("=", 1)[1])
                        assert max_age_val == expected_max_age
                        found_max_age = True
        assert found_max_age, "Session cookie must have Max-Age set"

    def test_session_token_stored_as_hash_in_db(self, app, client, session_user):
        """The raw token is NOT stored in the DB — only its SHA-256 hash."""
        token = _login_and_get_token(client)
        assert token is not None

        expected_hash = _hash_token(token)
        with app.app_context():
            session_record = Session.query.filter_by(token_hash=expected_hash).first()
            assert session_record is not None
            # The raw token should not appear anywhere in the session record
            assert session_record.token_hash != token
            assert session_record.token_hash == expected_hash
