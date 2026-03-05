"""Property-based tests for Role-Based Access Control (RBAC).

Feature: totika-audit-webapp
Property 7: RBAC enforcement — unauthorized access returns 403
Property 8: Role assignment accepts any valid combination

Uses Hypothesis for property-based testing with the Flask test client.
"""

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from flask import Blueprint, g

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME
from app.utils.rbac import (
    VALID_ROLES,
    _parse_roles,
    has_role,
    has_any_role,
    roles_required,
    login_required,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# All four valid roles
_ALL_ROLES = sorted(VALID_ROLES)  # ['admin', 'auditor', 'auditee', 'viewer']

# Strategy: a non-empty subset of valid roles (for Property 8)
_role_subset_st = st.frozensets(
    st.sampled_from(_ALL_ROLES), min_size=1, max_size=4
)

# Strategy: a single non-admin role
_non_admin_role_st = st.sampled_from(["auditor", "auditee", "viewer"])

# Strategy: a single role from the full set
_any_role_st = st.sampled_from(_ALL_ROLES)

# Suppress the function-scoped fixture health check
_suppress_fixture_check = settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


# ---------------------------------------------------------------------------
# Test app factory with RBAC-protected endpoints
# ---------------------------------------------------------------------------


import itertools

_user_counter = itertools.count()


def _create_rbac_pbt_app(tmp_path):
    """Create a Flask app with test endpoints protected by various role requirements."""

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'rbac_pbt.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)

    bp = Blueprint("rbac_pbt", __name__)

    @bp.route("/pbt/admin-only")
    @roles_required("admin")
    def admin_only():
        return "admin-ok"

    @bp.route("/pbt/auditor-only")
    @roles_required("auditor")
    def auditor_only():
        return "auditor-ok"

    @bp.route("/pbt/viewer-only")
    @roles_required("viewer")
    def viewer_only():
        return "viewer-ok"

    @bp.route("/pbt/auditee-only")
    @roles_required("auditee")
    def auditee_only():
        return "auditee-ok"

    @bp.route("/pbt/auditor-admin")
    @roles_required("auditor", "admin")
    def auditor_admin():
        return "auditor-admin-ok"

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    return app


def _unique_username(prefix):
    """Generate a unique username to avoid DB constraint violations across iterations."""
    return f"{prefix}_{next(_user_counter)}"


def _make_user_in_app(app, roles_str, username):
    """Create a user with the given roles in the app context and return (user_id, token)."""
    uname = _unique_username(username)
    with app.app_context():
        user = User(
            username=uname,
            email=f"{uname}@example.com",
            display_name=uname.title(),
            password_hash=hash_password("test-password"),
            roles=roles_str,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user.id, token


# Endpoint → required role(s) mapping
_ENDPOINTS = {
    "/pbt/admin-only": {"admin"},
    "/pbt/auditor-only": {"auditor"},
    "/pbt/viewer-only": {"viewer"},
    "/pbt/auditee-only": {"auditee"},
    "/pbt/auditor-admin": {"auditor", "admin"},
}


# ===========================================================================
# Property 7: RBAC enforcement — unauthorized access returns 403
# ===========================================================================


class TestProperty7RBACEnforcement:
    """Property 7: RBAC enforcement — unauthorized access returns 403.

    *For any* user-role and endpoint combination where the user lacks the
    required role, the response SHALL be 403 Forbidden. Specifically:
    non-Auditors cannot create/edit audits, non-Admins cannot access admin
    endpoints, Viewers can only read completed audits, and Auditees can only
    view audits where they are the subject.

    Admin always has full access (Req 2.6).

    **Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7**
    """

    @_suppress_fixture_check
    @given(
        user_role=_non_admin_role_st,
        endpoint=st.sampled_from(list(_ENDPOINTS.keys())),
    )
    def test_non_admin_without_required_role_gets_403(
        self, tmp_path, user_role, endpoint
    ):
        """A non-admin user without the required role gets 403."""
        required_roles = _ENDPOINTS[endpoint]

        # Only test when the user does NOT have any of the required roles
        assume(user_role not in required_roles)

        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        _, token = _make_user_in_app(
            app, user_role, f"user_{user_role}_{endpoint.replace('/', '_')}"
        )
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.get(endpoint)
        assert resp.status_code == 403, (
            f"Expected 403 for role={user_role} on {endpoint}, "
            f"got {resp.status_code}"
        )

    @_suppress_fixture_check
    @given(endpoint=st.sampled_from(list(_ENDPOINTS.keys())))
    def test_admin_always_has_access(self, tmp_path, endpoint):
        """Admin role grants access to every endpoint (Req 2.6)."""
        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        _, token = _make_user_in_app(
            app, "admin", f"admin_{endpoint.replace('/', '_')}"
        )
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.get(endpoint)
        assert resp.status_code == 200, (
            f"Expected 200 for admin on {endpoint}, got {resp.status_code}"
        )

    @_suppress_fixture_check
    @given(
        user_role=_any_role_st,
        endpoint=st.sampled_from(list(_ENDPOINTS.keys())),
    )
    def test_user_with_required_role_gets_200(self, tmp_path, user_role, endpoint):
        """A user with the required role (or admin) gets 200."""
        required_roles = _ENDPOINTS[endpoint]

        # Only test when the user HAS one of the required roles, or is admin
        assume(user_role in required_roles or user_role == "admin")

        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        _, token = _make_user_in_app(
            app, user_role, f"ok_{user_role}_{endpoint.replace('/', '_')}"
        )
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.get(endpoint)
        assert resp.status_code == 200, (
            f"Expected 200 for role={user_role} on {endpoint}, "
            f"got {resp.status_code}"
        )

    def test_viewer_cannot_access_auditor_endpoint(self, tmp_path):
        """Viewer cannot create/edit audits (auditor-only endpoint)."""
        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        _, token = _make_user_in_app(app, "viewer", "viewer_no_audit")
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.get("/pbt/auditor-only")
        assert resp.status_code == 403

    def test_auditee_cannot_access_admin_endpoint(self, tmp_path):
        """Auditee cannot access admin endpoints."""
        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        _, token = _make_user_in_app(app, "auditee", "auditee_no_admin")
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.get("/pbt/admin-only")
        assert resp.status_code == 403

    def test_unauthenticated_redirects_not_403(self, tmp_path):
        """Unauthenticated users are redirected to login, not given 403."""
        app = _create_rbac_pbt_app(tmp_path)
        client = app.test_client()

        resp = client.get("/pbt/admin-only")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ===========================================================================
# Property 8: Role assignment accepts any valid combination
# ===========================================================================


class TestProperty8RoleAssignment:
    """Property 8: Role assignment accepts any valid combination.

    *For any* non-empty subset of the four valid roles (Admin, Auditor,
    Auditee, Viewer), an Admin SHALL be able to assign that combination to
    a user, and the assigned roles SHALL be persisted correctly.

    **Validates: Requirements 2.2**
    """

    @_suppress_fixture_check
    @given(role_combo=_role_subset_st)
    def test_any_valid_role_combination_persists(self, tmp_path, role_combo):
        """Any non-empty subset of valid roles can be assigned and persisted."""
        app = _create_rbac_pbt_app(tmp_path)

        roles_str = ",".join(sorted(role_combo))
        username = _unique_username("combo")

        with app.app_context():
            user = User(
                username=username,
                email=f"{username}@example.com",
                display_name="Combo User",
                password_hash=hash_password("test-pw"),
                roles=roles_str,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            # Re-read from DB to verify persistence
            loaded = User.query.filter_by(username=username).first()
            assert loaded is not None
            persisted_roles = _parse_roles(loaded.roles)
            assert persisted_roles == set(role_combo), (
                f"Expected {role_combo}, got {persisted_roles}"
            )

    @_suppress_fixture_check
    @given(role_combo=_role_subset_st)
    def test_role_combination_grants_correct_access(self, tmp_path, role_combo):
        """A user with a role combination has access matching their roles."""
        app = _create_rbac_pbt_app(tmp_path)

        roles_str = ",".join(sorted(role_combo))
        username = _unique_username("access")

        _, token = _make_user_in_app(app, roles_str, username)
        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        for endpoint, required_roles in _ENDPOINTS.items():
            resp = client.get(endpoint)
            user_roles = set(role_combo)

            # Admin always has access; otherwise need overlap with required
            should_have_access = (
                "admin" in user_roles
                or bool(user_roles & required_roles)
            )

            if should_have_access:
                assert resp.status_code == 200, (
                    f"roles={role_combo} should access {endpoint}, "
                    f"got {resp.status_code}"
                )
            else:
                assert resp.status_code == 403, (
                    f"roles={role_combo} should NOT access {endpoint}, "
                    f"got {resp.status_code}"
                )

    @_suppress_fixture_check
    @given(role_combo=_role_subset_st)
    def test_has_role_matches_assigned_roles(self, tmp_path, role_combo):
        """has_role() returns True for each assigned role and False for others."""
        roles_str = ",".join(sorted(role_combo))
        user = User(
            username="rolecheck",
            email="rolecheck@example.com",
            display_name="Role Check",
            password_hash=hash_password("pw"),
            roles=roles_str,
            is_active=True,
        )

        for role in _ALL_ROLES:
            if role in role_combo:
                assert has_role(user, role), (
                    f"has_role should be True for {role} in {role_combo}"
                )
            else:
                assert not has_role(user, role), (
                    f"has_role should be False for {role} not in {role_combo}"
                )

    @_suppress_fixture_check
    @given(role_combo=_role_subset_st)
    def test_has_any_role_correct(self, tmp_path, role_combo):
        """has_any_role() returns True when checking against assigned roles."""
        roles_str = ",".join(sorted(role_combo))
        user = User(
            username="anyrolecheck",
            email="anyrolecheck@example.com",
            display_name="Any Role Check",
            password_hash=hash_password("pw"),
            roles=roles_str,
            is_active=True,
        )

        # Checking with the assigned roles should return True
        assert has_any_role(user, *role_combo), (
            f"has_any_role should be True for {role_combo}"
        )

        # Checking with roles the user does NOT have should return False
        missing_roles = set(_ALL_ROLES) - set(role_combo)
        if missing_roles:
            assert not has_any_role(user, *missing_roles), (
                f"has_any_role should be False for {missing_roles} "
                f"when user has {role_combo}"
            )
