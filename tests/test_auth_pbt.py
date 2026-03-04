"""Property-based tests for authentication.

Feature: totika-audit-webapp
Properties 1–3: Invalid credentials uniform error, MFA blocks session,
account lockout after consecutive failures.

Uses Hypothesis for property-based testing with the Flask test client.
"""

from datetime import datetime, timedelta

import pyotp
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app.extensions import db
from app.models.user import User, Session
from app.utils.auth import (
    SESSION_COOKIE_NAME,
    LOCKOUT_THRESHOLD,
    hash_password,
    _hash_token,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Usernames: printable, non-empty, no leading/trailing whitespace
_username_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() == s)

# Passwords: arbitrary non-empty strings
_password_st = st.text(min_size=1, max_size=60)

# Suppress the function-scoped fixture health check — our fixtures are safe
# to reuse across Hypothesis iterations (we reset state explicitly).
_suppress_fixture_check = settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


def _get_session_cookie(response):
    """Extract the session_token cookie value from a response."""
    for header_val in response.headers.getlist("Set-Cookie"):
        if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
            value = header_val.split("=", 1)[1].split(";")[0]
            if value:  # ignore empty (deleted) cookies
                return value
    return None



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KNOWN_USERNAME = "propuser"
KNOWN_PASSWORD = "known-correct-pw-123"
KNOWN_EMAIL = "propuser@example.com"


@pytest.fixture(autouse=False)
def prop_user(app):
    """Create a known user for property tests (no MFA)."""
    with app.app_context():
        user = User(
            username=KNOWN_USERNAME,
            email=KNOWN_EMAIL,
            display_name="Property User",
            password_hash=hash_password(KNOWN_PASSWORD),
            roles="auditor",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


@pytest.fixture(autouse=False)
def totp_user(app):
    """Create a user with TOTP MFA enabled."""
    with app.app_context():
        secret = pyotp.random_base32()
        user = User(
            username="totp_prop_user",
            email="totp_prop@example.com",
            display_name="TOTP Prop User",
            password_hash=hash_password("totp-correct-pw"),
            roles="auditor",
            is_active=True,
            mfa_type="totp",
            totp_secret=secret,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


@pytest.fixture(autouse=False)
def email_mfa_user(app):
    """Create a user with email MFA enabled."""
    with app.app_context():
        user = User(
            username="email_prop_user",
            email="email_prop@example.com",
            display_name="Email Prop User",
            password_hash=hash_password("email-correct-pw"),
            roles="auditor",
            is_active=True,
            mfa_type="email",
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user


def _reset_user_lockout(app, username):
    """Reset a user's lockout state within the app context."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.failed_login_count = 0
            user.locked_until = None
            db.session.commit()



# ===========================================================================
# Property 1: Invalid credentials return uniform error
# ===========================================================================


class TestProperty1UniformError:
    """Property 1: Invalid credentials return uniform error.

    *For any* login attempt with invalid credentials (wrong username, wrong
    password, or both), the error response message SHALL be identical
    regardless of which field was incorrect.

    **Validates: Requirements 1.2**
    """

    EXPECTED_ERROR = b"Invalid username or password"

    @_suppress_fixture_check
    @given(username=_username_st, password=_password_st)
    def test_wrong_username_same_error(self, app, client, prop_user, username, password):
        """Any non-existent username yields the uniform error message."""
        assume(username != KNOWN_USERNAME)

        resp = client.post("/login", data={"username": username, "password": password})
        assert resp.status_code == 401
        assert self.EXPECTED_ERROR in resp.data

    @_suppress_fixture_check
    @given(password=_password_st)
    def test_wrong_password_same_error(self, app, client, prop_user, password):
        """Correct username but any wrong password yields the same error."""
        assume(password != KNOWN_PASSWORD)
        # Reset lockout state before each iteration
        _reset_user_lockout(app, KNOWN_USERNAME)

        resp = client.post(
            "/login", data={"username": KNOWN_USERNAME, "password": password}
        )
        # Reset lockout after the attempt too (failed login increments counter)
        _reset_user_lockout(app, KNOWN_USERNAME)

        assert resp.status_code == 401
        assert self.EXPECTED_ERROR in resp.data

    @_suppress_fixture_check
    @given(username=_username_st, password=_password_st)
    def test_both_wrong_same_error(self, app, client, prop_user, username, password):
        """Both username and password wrong still yields the same error."""
        assume(username != KNOWN_USERNAME)
        assume(password != KNOWN_PASSWORD)

        resp = client.post("/login", data={"username": username, "password": password})
        assert resp.status_code == 401
        assert self.EXPECTED_ERROR in resp.data


# ===========================================================================
# Property 2: MFA blocks session issuance without valid code
# ===========================================================================


class TestProperty2MFABlocksSession:
    """Property 2: MFA blocks session issuance without valid code.

    *For any* user with MFA enabled (TOTP or email), after valid password
    verification, a Session_Token SHALL NOT be issued until a valid MFA code
    is provided.

    **Validates: Requirements 1.3, 1.4**
    """

    # --- TOTP MFA ---

    def test_totp_login_does_not_issue_session_cookie(self, app, client, totp_user):
        """Valid credentials with TOTP MFA must NOT issue a session cookie."""
        resp = client.post(
            "/login",
            data={"username": "totp_prop_user", "password": "totp-correct-pw"},
            follow_redirects=False,
        )
        # Should redirect to MFA page
        assert resp.status_code == 302
        assert "/login/mfa" in resp.headers["Location"]
        # No session cookie issued
        cookie = _get_session_cookie(resp)
        assert cookie is None

    def test_totp_no_session_in_db_before_mfa(self, app, client, totp_user):
        """After password-only login, no Session record should exist for the user."""
        client.post(
            "/login",
            data={"username": "totp_prop_user", "password": "totp-correct-pw"},
        )
        with app.app_context():
            count = Session.query.filter_by(user_id=totp_user.id).count()
            assert count == 0

    @_suppress_fixture_check
    @given(code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_totp_invalid_code_rejects(self, app, client, totp_user, code):
        """Any invalid TOTP code must be rejected without issuing a session."""
        with app.app_context():
            user = db.session.get(User, totp_user.id)
            totp = pyotp.TOTP(user.totp_secret)
            valid_code = totp.now()
        assume(code != valid_code)

        # Step 1: login with password
        client.post(
            "/login",
            data={"username": "totp_prop_user", "password": "totp-correct-pw"},
        )
        # Step 2: submit invalid code
        resp = client.post("/login/mfa", data={"code": code})
        assert resp.status_code == 401
        cookie = _get_session_cookie(resp)
        assert cookie is None

    def test_totp_valid_code_issues_session(self, app, client, totp_user):
        """A valid TOTP code after password verification issues a session."""
        client.post(
            "/login",
            data={"username": "totp_prop_user", "password": "totp-correct-pw"},
        )
        with app.app_context():
            user = db.session.get(User, totp_user.id)
            totp = pyotp.TOTP(user.totp_secret)
            valid_code = totp.now()

        resp = client.post(
            "/login/mfa", data={"code": valid_code}, follow_redirects=False
        )
        assert resp.status_code == 302
        cookie = _get_session_cookie(resp)
        assert cookie is not None

    # --- Email MFA ---

    def test_email_mfa_login_does_not_issue_session_cookie(
        self, app, client, email_mfa_user
    ):
        """Valid credentials with email MFA must NOT issue a session cookie."""
        resp = client.post(
            "/login",
            data={"username": "email_prop_user", "password": "email-correct-pw"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login/mfa" in resp.headers["Location"]
        cookie = _get_session_cookie(resp)
        assert cookie is None

    def test_email_mfa_no_session_in_db_before_mfa(
        self, app, client, email_mfa_user
    ):
        """After password-only login with email MFA, no Session record exists."""
        client.post(
            "/login",
            data={"username": "email_prop_user", "password": "email-correct-pw"},
        )
        with app.app_context():
            count = Session.query.filter_by(user_id=email_mfa_user.id).count()
            assert count == 0

    @_suppress_fixture_check
    @given(code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_email_mfa_invalid_code_rejects(
        self, app, client, email_mfa_user, code
    ):
        """Any wrong email MFA code must be rejected without issuing a session."""
        # Step 1: login with password
        client.post(
            "/login",
            data={"username": "email_prop_user", "password": "email-correct-pw"},
        )
        # Get the real code from the Flask session
        with client.session_transaction() as sess:
            real_code = sess.get("mfa_email_code")
        assume(code != real_code)

        # Step 2: submit wrong code
        resp = client.post("/login/mfa", data={"code": code})
        assert resp.status_code == 401
        cookie = _get_session_cookie(resp)
        assert cookie is None

    def test_email_mfa_valid_code_issues_session(
        self, app, client, email_mfa_user
    ):
        """The correct email MFA code issues a session cookie."""
        client.post(
            "/login",
            data={"username": "email_prop_user", "password": "email-correct-pw"},
        )
        with client.session_transaction() as sess:
            real_code = sess.get("mfa_email_code")
        assert real_code is not None

        resp = client.post(
            "/login/mfa", data={"code": real_code}, follow_redirects=False
        )
        assert resp.status_code == 302
        cookie = _get_session_cookie(resp)
        assert cookie is not None



# ===========================================================================
# Property 3: Account lockout after consecutive failures
# ===========================================================================


class TestProperty3AccountLockout:
    """Property 3: Account lockout after consecutive failures.

    *For any* user account, after exactly LOCKOUT_THRESHOLD (5) consecutive
    failed login attempts, the account SHALL be locked and reject further
    login attempts (even with valid credentials) for 15 minutes.

    **Validates: Requirements 1.6**
    """

    @_suppress_fixture_check
    @given(num_failures=st.integers(min_value=0, max_value=4))
    def test_fewer_than_threshold_does_not_lock(
        self, app, client, prop_user, num_failures
    ):
        """Fewer than LOCKOUT_THRESHOLD failures must NOT lock the account."""
        # Reset state before each iteration
        _reset_user_lockout(app, KNOWN_USERNAME)

        # Perform num_failures failed logins
        for _ in range(num_failures):
            client.post(
                "/login",
                data={"username": KNOWN_USERNAME, "password": "wrong-pw"},
            )

        # Account should NOT be locked — valid credentials should work
        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        cookie = _get_session_cookie(resp)
        assert cookie is not None

        # Clean up: reset for next iteration
        _reset_user_lockout(app, KNOWN_USERNAME)

    def test_exactly_threshold_locks_account(self, app, client, prop_user):
        """Exactly LOCKOUT_THRESHOLD (5) failures locks the account."""
        _reset_user_lockout(app, KNOWN_USERNAME)

        for _ in range(LOCKOUT_THRESHOLD):
            client.post(
                "/login",
                data={"username": KNOWN_USERNAME, "password": "wrong-pw"},
            )

        # Now even valid credentials should be rejected with 403
        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
        )
        assert resp.status_code == 403
        assert b"Account temporarily locked" in resp.data

    def test_locked_account_rejects_valid_credentials(self, app, client, prop_user):
        """A locked account rejects valid credentials with 403."""
        # Lock the account by performing LOCKOUT_THRESHOLD failed logins
        for _ in range(LOCKOUT_THRESHOLD):
            client.post(
                "/login",
                data={"username": KNOWN_USERNAME, "password": "wrong-pw"},
            )

        resp = client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
        )
        assert resp.status_code == 403
        assert b"Account temporarily locked" in resp.data

    def test_lockout_expires_after_duration(self, app, prop_user):
        """After lockout duration expires, valid credentials work again."""
        # Directly set the user as locked but with an expired lockout
        with app.app_context():
            user = User.query.filter_by(username=KNOWN_USERNAME).first()
            user.failed_login_count = LOCKOUT_THRESHOLD
            user.locked_until = datetime.utcnow() - timedelta(minutes=1)
            db.session.commit()

        # Use a fresh client so there's no stale session state
        test_client = app.test_client()
        resp = test_client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        cookie = _get_session_cookie(resp)
        assert cookie is not None

    def test_successful_login_resets_counter(self, app, client, prop_user):
        """A successful login resets the failed login counter to 0."""
        # Perform 3 failed logins to set the counter
        for _ in range(3):
            client.post(
                "/login",
                data={"username": KNOWN_USERNAME, "password": "wrong-pw"},
            )

        # Now login with correct credentials
        client.post(
            "/login",
            data={"username": KNOWN_USERNAME, "password": KNOWN_PASSWORD},
        )

        with app.app_context():
            user = User.query.filter_by(username=KNOWN_USERNAME).first()
            assert user.failed_login_count == 0
            assert user.locked_until is None
