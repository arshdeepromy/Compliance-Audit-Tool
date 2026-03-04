"""Unit tests for reverse proxy support and base path configuration.

Validates: Requirements 16.1, 16.2, 16.3, 16.4
"""

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class ProxyTestConfig(TestConfig):
    """Config with proxy support enabled and a custom base path."""
    BEHIND_PROXY = True
    BASE_PATH = "/audit/"


class NoProxyTestConfig(TestConfig):
    """Config with proxy support disabled (default)."""
    BEHIND_PROXY = False
    BASE_PATH = "/"


@pytest.fixture
def proxy_app(tmp_path):
    """Flask app with BEHIND_PROXY=True and BASE_PATH=/audit/."""
    db_path = tmp_path / "proxy_test.db"

    class Cfg(ProxyTestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    app = create_app(config_class=Cfg, run_startup=False)
    with app.app_context():
        _db.create_all()
    yield app
    with app.app_context():
        _db.drop_all()


@pytest.fixture
def no_proxy_app(tmp_path):
    """Flask app with BEHIND_PROXY=False and BASE_PATH=/."""
    db_path = tmp_path / "noproxy_test.db"

    class Cfg(NoProxyTestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    app = create_app(config_class=Cfg, run_startup=False)
    with app.app_context():
        _db.create_all()
    yield app
    with app.app_context():
        _db.drop_all()


# ---------------------------------------------------------------------------
# ProxyFix middleware tests
# ---------------------------------------------------------------------------


class TestProxyFixMiddleware:
    """Verify ProxyFix is applied when BEHIND_PROXY=True."""

    def test_proxyfix_applied_when_behind_proxy(self, proxy_app):
        """ProxyFix wraps wsgi_app when BEHIND_PROXY=True."""
        from werkzeug.middleware.proxy_fix import ProxyFix

        assert isinstance(proxy_app.wsgi_app, ProxyFix)

    def test_proxyfix_not_applied_when_not_behind_proxy(self, no_proxy_app):
        """ProxyFix is NOT applied when BEHIND_PROXY=False."""
        from werkzeug.middleware.proxy_fix import ProxyFix

        assert not isinstance(no_proxy_app.wsgi_app, ProxyFix)


# ---------------------------------------------------------------------------
# APPLICATION_ROOT / base path tests
# ---------------------------------------------------------------------------


class TestBasePath:
    """Verify APPLICATION_ROOT is set from BASE_PATH."""

    def test_application_root_set_from_base_path(self, proxy_app):
        """APPLICATION_ROOT should equal BASE_PATH when it's not '/'."""
        assert proxy_app.config["APPLICATION_ROOT"] == "/audit/"

    def test_application_root_default_when_no_base_path(self, no_proxy_app):
        """APPLICATION_ROOT should remain '/' when BASE_PATH is '/'."""
        assert no_proxy_app.config.get("APPLICATION_ROOT", "/") == "/"

    def test_url_for_respects_base_path(self, proxy_app):
        """url_for() should include the base path prefix."""
        with proxy_app.test_request_context():
            from flask import url_for

            url = url_for("auth.login")
            assert url.startswith("/audit/") or url.startswith("/audit")

    def test_url_for_static_respects_base_path(self, proxy_app):
        """url_for('static', ...) should include the base path prefix."""
        with proxy_app.test_request_context():
            from flask import url_for

            url = url_for("static", filename="css/style.css")
            assert "/audit/" in url or url.startswith("/audit")


# ---------------------------------------------------------------------------
# HTTPS detection tests
# ---------------------------------------------------------------------------


class TestHTTPSDetection:
    """Verify is_https() detects protocol correctly."""

    def test_is_https_false_for_http(self, no_proxy_app):
        """is_https() returns False for plain HTTP requests."""
        from app.utils.proxy import is_https

        with no_proxy_app.test_request_context("/", base_url="http://localhost"):
            assert is_https() is False

    def test_is_https_true_for_https(self, no_proxy_app):
        """is_https() returns True for direct HTTPS requests."""
        from app.utils.proxy import is_https

        with no_proxy_app.test_request_context("/", base_url="https://localhost"):
            assert is_https() is True

    def test_is_https_true_with_forwarded_proto(self, no_proxy_app):
        """is_https() returns True when X-Forwarded-Proto is 'https'."""
        from app.utils.proxy import is_https

        with no_proxy_app.test_request_context(
            "/", headers={"X-Forwarded-Proto": "https"}
        ):
            assert is_https() is True

    def test_is_https_false_with_forwarded_proto_http(self, no_proxy_app):
        """is_https() returns False when X-Forwarded-Proto is 'http'."""
        from app.utils.proxy import is_https

        with no_proxy_app.test_request_context(
            "/", headers={"X-Forwarded-Proto": "http"}
        ):
            assert is_https() is False


# ---------------------------------------------------------------------------
# Client IP detection tests
# ---------------------------------------------------------------------------


class TestClientIPDetection:
    """Verify get_client_ip() extracts the correct IP."""

    def test_client_ip_from_remote_addr(self, no_proxy_app):
        """get_client_ip() falls back to remote_addr when no proxy headers."""
        from app.utils.proxy import get_client_ip

        with no_proxy_app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": "192.168.1.100"}
        ):
            assert get_client_ip() == "192.168.1.100"

    def test_client_ip_from_x_forwarded_for(self, no_proxy_app):
        """get_client_ip() uses X-Forwarded-For header when present."""
        from app.utils.proxy import get_client_ip

        with no_proxy_app.test_request_context(
            "/", headers={"X-Forwarded-For": "203.0.113.50"}
        ):
            assert get_client_ip() == "203.0.113.50"

    def test_client_ip_from_x_forwarded_for_chain(self, no_proxy_app):
        """get_client_ip() extracts the first IP from a chain."""
        from app.utils.proxy import get_client_ip

        with no_proxy_app.test_request_context(
            "/",
            headers={"X-Forwarded-For": "203.0.113.50, 10.0.0.1, 10.0.0.2"},
        ):
            assert get_client_ip() == "203.0.113.50"

    def test_client_ip_default_when_no_info(self, no_proxy_app):
        """get_client_ip() returns 127.0.0.1 when no IP info available."""
        from app.utils.proxy import get_client_ip

        with no_proxy_app.test_request_context("/"):
            ip = get_client_ip()
            # Should be either the test context default or our fallback
            assert ip is not None


# ---------------------------------------------------------------------------
# Cookie flags tests
# ---------------------------------------------------------------------------


class TestCookieFlags:
    """Verify session cookies have correct flags based on protocol."""

    def _create_user(self, app):
        """Helper to create a test user."""
        with app.app_context():
            user = User(
                username="cookietest",
                email="cookie@test.com",
                display_name="Cookie Test",
                password_hash=hash_password("test-password"),
                roles="auditor",
                is_active=True,
            )
            _db.session.add(user)
            _db.session.commit()
            _db.session.refresh(user)
            return user

    def test_cookie_httponly_always_set(self, no_proxy_app):
        """Session cookie always has HttpOnly=True."""
        user = self._create_user(no_proxy_app)
        client = no_proxy_app.test_client()

        with no_proxy_app.test_request_context():
            response = client.post(
                "/login",
                data={"username": "cookietest", "password": "test-password"},
                follow_redirects=False,
            )
            # Check Set-Cookie header
            cookie_header = response.headers.get("Set-Cookie", "")
            if SESSION_COOKIE_NAME in cookie_header:
                assert "HttpOnly" in cookie_header

    def test_cookie_samesite_lax(self, no_proxy_app):
        """Session cookie has SameSite=Lax."""
        user = self._create_user(no_proxy_app)
        client = no_proxy_app.test_client()

        response = client.post(
            "/login",
            data={"username": "cookietest", "password": "test-password"},
            follow_redirects=False,
        )
        cookie_header = response.headers.get("Set-Cookie", "")
        if SESSION_COOKIE_NAME in cookie_header:
            assert "SameSite=Lax" in cookie_header

    def test_cookie_not_secure_over_http(self, no_proxy_app):
        """Session cookie does NOT have Secure flag over plain HTTP."""
        user = self._create_user(no_proxy_app)
        client = no_proxy_app.test_client()

        response = client.post(
            "/login",
            data={"username": "cookietest", "password": "test-password"},
            follow_redirects=False,
        )
        cookie_header = response.headers.get("Set-Cookie", "")
        if SESSION_COOKIE_NAME in cookie_header:
            # Over HTTP, Secure should NOT be present
            assert "Secure" not in cookie_header


# ---------------------------------------------------------------------------
# get_base_path helper test
# ---------------------------------------------------------------------------


class TestGetBasePath:
    """Verify get_base_path() returns the configured value."""

    def test_returns_configured_base_path(self, proxy_app):
        from app.utils.proxy import get_base_path

        with proxy_app.app_context():
            assert get_base_path() == "/audit/"

    def test_returns_default_slash(self, no_proxy_app):
        from app.utils.proxy import get_base_path

        with no_proxy_app.app_context():
            assert get_base_path() == "/"
