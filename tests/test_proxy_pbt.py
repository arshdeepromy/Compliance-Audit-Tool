"""Property-based tests for reverse proxy support.

Feature: totika-audit-webapp
Property 29: Base path prefix applied to all generated URLs
Property 30: Proxy headers determine client IP and protocol

Uses Hypothesis for property-based testing with the Flask test client.
"""

import re

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.utils.proxy import is_https, get_client_ip


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Base path segments: alphanumeric + hyphens, like real proxy sub-paths
_path_segment_st = st.from_regex(r"[a-z][a-z0-9\-]{0,15}", fullmatch=True)

# Full base paths: /segment/ or /seg1/seg2/ — always start and end with /
_base_path_st = st.lists(
    _path_segment_st,
    min_size=1,
    max_size=3,
).map(lambda segs: "/" + "/".join(segs) + "/")

# Endpoint names that exist in the app and can be called without arguments
_simple_endpoints = st.sampled_from([
    "auth.login",
    "audits.audit_list",
    "admin.branding",
    "admin.users_list",
    "admin.activity_logs",
    "templates.template_list",
])

# IPv4 addresses
_ipv4_st = st.tuples(
    st.integers(min_value=1, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=1, max_value=254),
).map(lambda t: f"{t[0]}.{t[1]}.{t[2]}.{t[3]}")

# Proxy chain: 1-4 IPs separated by commas
_forwarded_for_chain_st = st.lists(
    _ipv4_st,
    min_size=1,
    max_size=4,
).map(lambda ips: ", ".join(ips))

# Protocol values
_proto_st = st.sampled_from(["http", "https"])

# Suppress the function-scoped fixture health check
_suppress = settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, base_path):
    """Create a Flask app with the given BASE_PATH."""

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'proxy_pbt.db'}"
        BASE_PATH = base_path
        BEHIND_PROXY = True

    app = create_app(config_class=Cfg, run_startup=False)
    with app.app_context():
        _db.create_all()
    return app


# ===========================================================================
# Property 29: Base path prefix applied to all generated URLs
# ===========================================================================


class TestProperty29BasePathPrefix:
    """Property 29: Base path prefix applied to all generated URLs.

    *For any* base path string (e.g. "/app/", "/audit/", "/my-tool/"):
    when APPLICATION_ROOT is set to that path, url_for() should generate
    URLs that include the prefix.

    **Validates: Requirements 16.2, 16.3**
    """

    @_suppress
    @given(base_path=_base_path_st, endpoint=_simple_endpoints)
    def test_url_for_includes_base_path_prefix(self, tmp_path, base_path, endpoint):
        """url_for() generates URLs that start with the configured base path."""
        app = _make_app(tmp_path, base_path)
        try:
            with app.test_request_context():
                from flask import url_for

                url = url_for(endpoint)
                assert url.startswith(base_path) or url.startswith(base_path.rstrip("/")), (
                    f"url_for('{endpoint}') = '{url}' does not start with base path '{base_path}'"
                )
        finally:
            with app.app_context():
                _db.drop_all()

    @_suppress
    @given(base_path=_base_path_st)
    def test_static_url_includes_base_path(self, tmp_path, base_path):
        """url_for('static', ...) includes the base path prefix."""
        app = _make_app(tmp_path, base_path)
        try:
            with app.test_request_context():
                from flask import url_for

                url = url_for("static", filename="css/style.css")
                assert base_path.rstrip("/") in url, (
                    f"Static URL '{url}' does not contain base path '{base_path}'"
                )
        finally:
            with app.app_context():
                _db.drop_all()

    @_suppress
    @given(base_path=_base_path_st)
    def test_application_root_matches_base_path(self, tmp_path, base_path):
        """APPLICATION_ROOT config should equal the configured BASE_PATH."""
        app = _make_app(tmp_path, base_path)
        try:
            assert app.config["APPLICATION_ROOT"] == base_path
        finally:
            with app.app_context():
                _db.drop_all()


# ===========================================================================
# Property 30: Proxy headers determine client IP and protocol
# ===========================================================================


class TestProperty30ProxyHeaders:
    """Property 30: Proxy headers determine client IP and protocol.

    *For any* IP address string in X-Forwarded-For header:
    - get_client_ip() should return the first IP from the chain

    *For any* X-Forwarded-Proto header:
    - is_https() should return True when proto is "https", False when "http"

    **Validates: Requirements 16.1, 16.4**
    """

    @_suppress
    @given(ip_chain=_forwarded_for_chain_st)
    def test_get_client_ip_returns_first_ip_from_chain(self, app, ip_chain):
        """get_client_ip() extracts the first IP from X-Forwarded-For chain."""
        expected_ip = ip_chain.split(",")[0].strip()

        with app.test_request_context(
            "/", headers={"X-Forwarded-For": ip_chain}
        ):
            result = get_client_ip()
            assert result == expected_ip, (
                f"Expected '{expected_ip}' from chain '{ip_chain}', got '{result}'"
            )

    @_suppress
    @given(single_ip=_ipv4_st)
    def test_get_client_ip_returns_single_ip(self, app, single_ip):
        """get_client_ip() returns the IP when X-Forwarded-For has a single value."""
        with app.test_request_context(
            "/", headers={"X-Forwarded-For": single_ip}
        ):
            result = get_client_ip()
            assert result == single_ip

    @_suppress
    @given(proto=_proto_st)
    def test_is_https_matches_forwarded_proto(self, app, proto):
        """is_https() returns True for 'https', False for 'http'."""
        with app.test_request_context(
            "/", headers={"X-Forwarded-Proto": proto}
        ):
            result = is_https()
            if proto == "https":
                assert result is True, "is_https() should be True for proto='https'"
            else:
                assert result is False, "is_https() should be False for proto='http'"

    @_suppress
    @given(proto=st.sampled_from(["HTTPS", "Https", "hTTpS"]))
    def test_is_https_case_insensitive(self, app, proto):
        """is_https() handles case-insensitive X-Forwarded-Proto values."""
        with app.test_request_context(
            "/", headers={"X-Forwarded-Proto": proto}
        ):
            result = is_https()
            assert result is True, (
                f"is_https() should be True for proto='{proto}' (case-insensitive)"
            )

    @_suppress
    @given(ip=_ipv4_st)
    def test_get_client_ip_without_header_uses_remote_addr(self, app, ip):
        """get_client_ip() falls back to remote_addr when no X-Forwarded-For."""
        with app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": ip}
        ):
            result = get_client_ip()
            assert result == ip
