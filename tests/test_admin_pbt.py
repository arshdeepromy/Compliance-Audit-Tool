"""Property-based tests for admin features.

Feature: totika-audit-webapp
Properties 22–26: Branding round-trip, SMTP password encryption,
email features disabled without SMTP, user creation validation,
user deactivation invalidates access.

Uses Hypothesis for property-based testing with the Flask test client.
"""

import re

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app.extensions import db
from app.models.settings import BrandingSettings, SMTPSettings
from app.models.user import User, Session
from app.utils.auth import (
    SESSION_COOKIE_NAME,
    hash_password,
    create_session,
    invalidate_all_sessions,
)
from app.utils.encryption import encrypt_value, decrypt_value


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Company names: non-empty printable text
_company_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=100,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# Hex colour: valid 6-digit hex colour codes
_hex_colour_st = st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True)

# Passwords for SMTP: non-empty strings (avoid null bytes which break Fernet)
_smtp_password_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=80,
)

# Usernames for user creation
_username_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

# Emails
_email_st = st.from_regex(
    r"[a-z][a-z0-9]{0,10}@example\.com", fullmatch=True
)

# Display names
_display_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
    min_size=1,
    max_size=60,
).filter(lambda s: s.strip() != "")

# Passwords for user creation
_password_st = st.text(min_size=1, max_size=40)

# Valid roles
_VALID_ROLES = ["admin", "auditor", "auditee", "viewer"]
_roles_st = st.lists(
    st.sampled_from(_VALID_ROLES), min_size=1, max_size=4, unique=True
)

# Suppress the function-scoped fixture health check
_suppress_fixture_check = settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


def _get_session_cookie(response):
    """Extract the session_token cookie value from a response."""
    for header_val in response.headers.getlist("Set-Cookie"):
        if header_val.startswith(f"{SESSION_COOKIE_NAME}="):
            value = header_val.split("=", 1)[1].split(";")[0]
            if value:
                return value
    return None


def _login_as_admin(app, client):
    """Create an admin user and log in, returning the user."""
    with app.app_context():
        admin = User.query.filter_by(username="admin_pbt").first()
        if not admin:
            admin = User(
                username="admin_pbt",
                email="admin_pbt@example.com",
                display_name="Admin PBT",
                password_hash=hash_password("admin-pw-123"),
                roles="admin",
                is_active=True,
            )
            db.session.add(admin)
            db.session.commit()
            db.session.refresh(admin)

        # Create a session and set cookie on the client
        token = create_session(admin, ip="127.0.0.1")

    client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
    return admin


# ===========================================================================
# Property 22: Branding settings round-trip persistence
# ===========================================================================


class TestProperty22BrandingRoundTrip:
    """Property 22: Branding settings round-trip persistence.

    *For any* branding settings (company name, primary colour, accent colour),
    saving then loading SHALL produce equivalent values.

    **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
    """

    @_suppress_fixture_check
    @given(
        company_name=_company_name_st,
        primary_colour=_hex_colour_st,
        accent_colour=_hex_colour_st,
    )
    def test_branding_round_trip_via_model(
        self, app, company_name, primary_colour, accent_colour
    ):
        """Saving branding settings directly to DB and reading back produces
        identical values."""
        with app.app_context():
            branding = db.session.get(BrandingSettings, 1)
            if branding is None:
                branding = BrandingSettings(id=1)
                db.session.add(branding)

            branding.company_name = company_name
            branding.primary_colour = primary_colour
            branding.accent_colour = accent_colour
            db.session.commit()

            # Re-read from DB
            db.session.expire_all()
            loaded = db.session.get(BrandingSettings, 1)
            assert loaded is not None
            assert loaded.company_name == company_name
            assert loaded.primary_colour == primary_colour
            assert loaded.accent_colour == accent_colour

    @_suppress_fixture_check
    @given(
        company_name=_company_name_st,
        primary_colour=_hex_colour_st,
        accent_colour=_hex_colour_st,
    )
    def test_branding_round_trip_via_endpoint(
        self, app, client, company_name, primary_colour, accent_colour
    ):
        """POST to /admin/branding then GET should reflect saved values."""
        _login_as_admin(app, client)

        resp = client.post(
            "/admin/branding",
            data={
                "company_name": company_name,
                "primary_colour": primary_colour,
                "accent_colour": accent_colour,
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # Verify in DB
        with app.app_context():
            branding = db.session.get(BrandingSettings, 1)
            assert branding is not None
            assert branding.company_name == company_name
            assert branding.primary_colour == primary_colour
            assert branding.accent_colour == accent_colour


# ===========================================================================
# Property 23: SMTP password encrypted at rest
# ===========================================================================


class TestProperty23SMTPPasswordEncrypted:
    """Property 23: SMTP password encrypted at rest.

    *For any* password string: encrypt_value(password) should not contain
    the plaintext, and decrypt_value(encrypt_value(password)) should equal
    the original.

    **Validates: Requirements 12.1**
    """

    @_suppress_fixture_check
    @given(password=_smtp_password_st)
    def test_encrypted_value_not_plaintext(self, app, password):
        """The encrypted form must not contain the plaintext password."""
        with app.app_context():
            encrypted = encrypt_value(password)
            # The encrypted value should not be the same as plaintext
            assert encrypted != password
            # The plaintext should not appear as a substring of the ciphertext
            # (only check for passwords long enough to be meaningful)
            if len(password) >= 3:
                assert password not in encrypted

    @_suppress_fixture_check
    @given(password=_smtp_password_st)
    def test_encrypt_decrypt_round_trip(self, app, password):
        """Encrypting then decrypting must return the original password."""
        with app.app_context():
            encrypted = encrypt_value(password)
            decrypted = decrypt_value(encrypted)
            assert decrypted == password

    @_suppress_fixture_check
    @given(password=_smtp_password_st)
    def test_smtp_password_stored_encrypted_in_db(self, app, password):
        """When SMTP password is saved via the model, the DB column holds
        encrypted (non-plaintext) data that decrypts to the original."""
        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)

            smtp.password_encrypted = encrypt_value(password)
            db.session.commit()

            db.session.expire_all()
            loaded = db.session.get(SMTPSettings, 1)
            assert loaded.password_encrypted != password
            assert decrypt_value(loaded.password_encrypted) == password


# ===========================================================================
# Property 24: Email features disabled without SMTP
# ===========================================================================


class TestProperty24EmailDisabledWithoutSMTP:
    """Property 24: Email features disabled without SMTP.

    When SMTP host is None/empty: send_email() should return False.

    **Validates: Requirements 12.3**
    """

    def test_send_email_returns_false_when_no_smtp_settings(self, app):
        """send_email returns False when no SMTPSettings row exists."""
        from app.services.mailer import send_email

        with app.app_context():
            # Ensure no SMTP settings exist
            smtp = db.session.get(SMTPSettings, 1)
            if smtp:
                db.session.delete(smtp)
                db.session.commit()

            result = send_email("test@example.com", "Test", "Body")
            assert result is False

    def test_send_email_returns_false_when_host_is_none(self, app):
        """send_email returns False when SMTP host is None."""
        from app.services.mailer import send_email

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)
            smtp.host = None
            smtp.sender_address = "sender@example.com"
            db.session.commit()

            result = send_email("test@example.com", "Test", "Body")
            assert result is False

    def test_send_email_returns_false_when_host_is_empty(self, app):
        """send_email returns False when SMTP host is empty string."""
        from app.services.mailer import send_email

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)
            smtp.host = ""
            smtp.sender_address = "sender@example.com"
            db.session.commit()

            result = send_email("test@example.com", "Test", "Body")
            assert result is False

    @_suppress_fixture_check
    @given(
        to=_email_st,
        subject=st.text(min_size=1, max_size=50),
        body=st.text(min_size=1, max_size=200),
    )
    def test_send_email_always_false_without_smtp(self, app, to, subject, body):
        """For any email parameters, send_email returns False when SMTP
        is not configured."""
        from app.services.mailer import send_email

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)
            smtp.host = None
            smtp.sender_address = None
            db.session.commit()

            result = send_email(to, subject, body)
            assert result is False


# ===========================================================================
# Property 25: User creation requires all mandatory fields
# ===========================================================================


class TestProperty25UserCreationMandatoryFields:
    """Property 25: User creation requires all mandatory fields.

    *For any* combination of missing fields (username, email, display_name,
    password, roles): POST to /admin/users/new should return 400.

    **Validates: Requirements 13.1**
    """

    # The mandatory fields for user creation
    MANDATORY_FIELDS = ["username", "email", "display_name", "password", "roles"]

    @_suppress_fixture_check
    @given(
        missing_field=st.sampled_from(
            ["username", "email", "display_name", "password", "roles"]
        ),
        username=_username_st,
        email=_email_st,
        display_name=_display_name_st,
        password=_password_st,
    )
    def test_missing_single_field_returns_400(
        self, app, client, missing_field, username, email, display_name, password
    ):
        """Omitting any single mandatory field should return 400."""
        _login_as_admin(app, client)

        data = {
            "username": username,
            "email": email,
            "display_name": display_name,
            "password": password,
            "roles": "auditor",
        }
        # Remove the field being tested
        del data[missing_field]

        resp = client.post("/admin/users/new", data=data)
        assert resp.status_code == 400

    @_suppress_fixture_check
    @given(
        username=_username_st,
        email=_email_st,
        display_name=_display_name_st,
        password=_password_st,
        roles=_roles_st,
    )
    def test_all_fields_present_succeeds(
        self, app, client, username, email, display_name, password, roles
    ):
        """When all mandatory fields are present, user creation succeeds."""
        _login_as_admin(app, client)

        # Ensure no conflicts with existing users
        with app.app_context():
            existing = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            assume(existing is None)

        data = {
            "username": username,
            "email": email,
            "display_name": display_name,
            "password": password,
        }
        # Add roles as multiple form values
        resp = client.post(
            "/admin/users/new",
            data={**data, "roles": roles},
        )
        # Should redirect on success (302) or return 200
        assert resp.status_code in (200, 302)


# ===========================================================================
# Property 26: User deactivation invalidates access
# ===========================================================================


class TestProperty26UserDeactivationInvalidatesAccess:
    """Property 26: User deactivation invalidates access.

    After deactivating a user: their sessions should be deleted, and they
    should not be able to access protected routes.

    **Validates: Requirements 13.3**
    """

    def test_deactivation_deletes_sessions(self, app):
        """Deactivating a user removes all their session records."""
        with app.app_context():
            user = User(
                username="deact_user",
                email="deact@example.com",
                display_name="Deact User",
                password_hash=hash_password("deact-pw"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            # Create sessions for this user
            token1 = create_session(user, ip="127.0.0.1")
            token2 = create_session(user, ip="127.0.0.2")

            # Verify sessions exist
            session_count = Session.query.filter_by(user_id=user.id).count()
            assert session_count == 2

            # Deactivate: set is_active=False and invalidate sessions
            user.is_active = False
            invalidate_all_sessions(user.id)

            session_count = Session.query.filter_by(user_id=user.id).count()
            assert session_count == 0

    def test_deactivated_user_cannot_login(self, app, client):
        """A deactivated user cannot log in even with valid credentials."""
        with app.app_context():
            user = User(
                username="deact_login",
                email="deact_login@example.com",
                display_name="Deact Login",
                password_hash=hash_password("deact-login-pw"),
                roles="auditor",
                is_active=False,
            )
            db.session.add(user)
            db.session.commit()

        resp = client.post(
            "/login",
            data={"username": "deact_login", "password": "deact-login-pw"},
        )
        # Should not succeed — either 401 or no session cookie
        cookie = _get_session_cookie(resp)
        assert cookie is None
        assert resp.status_code in (401, 403)

    def test_deactivated_user_session_rejected(self, app):
        """An existing session for a deactivated user is rejected on
        subsequent requests."""
        with app.app_context():
            user = User(
                username="deact_sess",
                email="deact_sess@example.com",
                display_name="Deact Sess",
                password_hash=hash_password("deact-sess-pw"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)

            token = create_session(user, ip="127.0.0.1")

        # Use the token to make a request
        test_client = app.test_client()
        test_client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        # Deactivate the user
        with app.app_context():
            user = User.query.filter_by(username="deact_sess").first()
            user.is_active = False
            invalidate_all_sessions(user.id)
            db.session.commit()

        # Now the session should be rejected — request to a protected route
        resp = test_client.get("/admin/users", follow_redirects=False)
        # Should redirect to login or return 401/403
        assert resp.status_code in (302, 401, 403)

    def test_admin_deactivate_endpoint_invalidates_sessions(self, app, client):
        """Using the admin endpoint to deactivate a user invalidates their
        sessions."""
        admin = _login_as_admin(app, client)

        with app.app_context():
            target = User(
                username="target_deact",
                email="target_deact@example.com",
                display_name="Target Deact",
                password_hash=hash_password("target-pw"),
                roles="auditor",
                is_active=True,
            )
            db.session.add(target)
            db.session.commit()
            db.session.refresh(target)
            target_id = target.id

            # Create a session for the target user
            target_token = create_session(target, ip="10.0.0.1")

            # Verify session exists
            assert Session.query.filter_by(user_id=target_id).count() == 1

        # Admin deactivates the user via the endpoint
        resp = client.post(
            f"/admin/users/{target_id}",
            data={"action": "deactivate"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # Verify user is deactivated and sessions are gone
        with app.app_context():
            target = db.session.get(User, target_id)
            assert target.is_active is False
            assert Session.query.filter_by(user_id=target_id).count() == 0
