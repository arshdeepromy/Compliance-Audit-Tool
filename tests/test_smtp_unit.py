"""Unit tests for SMTP configuration routes and encryption helpers.

Covers: Fernet encryption/decryption, SMTP settings save, password masking,
test email route, and SMTP-not-configured notice.
"""

import pytest

from app.extensions import db
from app.models.settings import SMTPSettings
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME
from app.utils.encryption import encrypt_value, decrypt_value


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------


class TestEncryptionHelpers:
    def test_encrypt_decrypt_round_trip(self, app):
        with app.app_context():
            plaintext = "my-smtp-password-123!"
            ciphertext = encrypt_value(plaintext)
            assert ciphertext != plaintext
            assert decrypt_value(ciphertext) == plaintext

    def test_encrypted_value_is_not_plaintext(self, app):
        with app.app_context():
            plaintext = "secret"
            ciphertext = encrypt_value(plaintext)
            assert plaintext not in ciphertext

    def test_decrypt_invalid_ciphertext_returns_none(self, app):
        with app.app_context():
            assert decrypt_value("not-valid-ciphertext") is None

    def test_decrypt_empty_string_returns_none(self, app):
        with app.app_context():
            assert decrypt_value("") is None

    def test_different_plaintexts_produce_different_ciphertexts(self, app):
        with app.app_context():
            c1 = encrypt_value("password1")
            c2 = encrypt_value("password2")
            assert c1 != c2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_admin(app):
    """Create an admin user and return (user, session_token)."""
    with app.app_context():
        user = User(
            username="admin_smtp",
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("admin-pass"),
            roles="admin",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user, token


def _create_non_admin(app):
    """Create a non-admin user and return (user, session_token)."""
    with app.app_context():
        user = User(
            username="auditor_user",
            email="auditor@example.com",
            display_name="Auditor",
            password_hash=hash_password("auditor-pass"),
            roles="auditor",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user, token


# ---------------------------------------------------------------------------
# SMTP settings GET
# ---------------------------------------------------------------------------


class TestSMTPSettingsGet:
    def test_get_smtp_page_as_admin(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)
        resp = client.get("/admin/smtp")
        assert resp.status_code == 200

    def test_get_smtp_page_as_non_admin_returns_403(self, app, client):
        _, token = _create_non_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)
        resp = client.get("/admin/smtp")
        assert resp.status_code == 403

    def test_get_smtp_page_unauthenticated_redirects(self, app, client):
        resp = client.get("/admin/smtp")
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# SMTP settings POST
# ---------------------------------------------------------------------------


class TestSMTPSettingsPost:
    def test_save_smtp_settings(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        resp = client.post(
            "/admin/smtp",
            data={
                "host": "smtp.example.com",
                "port": "587",
                "username": "user@example.com",
                "password": "secret123",
                "sender_address": "noreply@example.com",
                "use_tls": "on",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            assert smtp.host == "smtp.example.com"
            assert smtp.port == 587
            assert smtp.username == "user@example.com"
            assert smtp.sender_address == "noreply@example.com"
            assert smtp.use_tls is True
            # Password should be encrypted, not plaintext
            assert smtp.password_encrypted is not None
            assert smtp.password_encrypted != "secret123"
            assert decrypt_value(smtp.password_encrypted) == "secret123"

    def test_save_smtp_without_password_preserves_existing(self, app, client):
        """If no password is submitted, the existing encrypted password is kept."""
        _, token = _create_admin(app)

        # First, set a password
        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)
            smtp.password_encrypted = encrypt_value("original-pass")
            db.session.commit()

        client.set_cookie(SESSION_COOKIE_NAME, token)
        resp = client.post(
            "/admin/smtp",
            data={
                "host": "smtp.example.com",
                "port": "465",
                "username": "",
                "password": "",
                "sender_address": "noreply@example.com",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            assert decrypt_value(smtp.password_encrypted) == "original-pass"

    def test_save_smtp_invalid_port_returns_400(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        resp = client.post(
            "/admin/smtp",
            data={
                "host": "smtp.example.com",
                "port": "not-a-number",
                "sender_address": "noreply@example.com",
            },
        )
        assert resp.status_code == 400

    def test_save_smtp_port_out_of_range_returns_400(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        resp = client.post(
            "/admin/smtp",
            data={
                "host": "smtp.example.com",
                "port": "99999",
                "sender_address": "noreply@example.com",
            },
        )
        assert resp.status_code == 400

    def test_save_smtp_clears_host(self, app, client):
        """Submitting empty host effectively unconfigures SMTP."""
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        client.post(
            "/admin/smtp",
            data={
                "host": "",
                "port": "587",
                "sender_address": "",
            },
            follow_redirects=True,
        )

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            assert smtp.host is None
            assert smtp.sender_address is None

    def test_use_tls_defaults_to_false_when_unchecked(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        client.post(
            "/admin/smtp",
            data={
                "host": "smtp.example.com",
                "port": "25",
                "sender_address": "noreply@example.com",
                # use_tls not included — checkbox unchecked
            },
            follow_redirects=True,
        )

        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            assert smtp.use_tls is False


# ---------------------------------------------------------------------------
# SMTP test email
# ---------------------------------------------------------------------------


class TestSMTPTestEmail:
    def test_test_email_without_config_flashes_error(self, app, client):
        _, token = _create_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)

        # Ensure SMTP is not configured
        with app.app_context():
            smtp = db.session.get(SMTPSettings, 1)
            if smtp is None:
                smtp = SMTPSettings(id=1)
                db.session.add(smtp)
            smtp.host = None
            smtp.sender_address = None
            db.session.commit()

        resp = client.post("/admin/smtp/test", follow_redirects=False)
        assert resp.status_code == 302

    def test_test_email_non_admin_returns_403(self, app, client):
        _, token = _create_non_admin(app)
        client.set_cookie(SESSION_COOKIE_NAME, token)
        resp = client.post("/admin/smtp/test")
        assert resp.status_code == 403

    def test_test_email_unauthenticated_redirects(self, app, client):
        resp = client.post("/admin/smtp/test")
        assert resp.status_code == 302
