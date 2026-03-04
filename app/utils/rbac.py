"""Role-Based Access Control (RBAC) decorators and utilities.

Provides decorators for protecting Flask endpoints based on user roles.
The four supported roles are: Admin, Auditor, Auditee, Viewer.

Role checking is performed against ``g.current_user.roles`` which is a
comma-separated string set by the session middleware in ``utils/auth.py``.
"""

from functools import wraps

from flask import abort, g, redirect, url_for


# ---------------------------------------------------------------------------
# Valid roles
# ---------------------------------------------------------------------------

VALID_ROLES = {"admin", "auditor", "auditee", "viewer"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_roles(roles_str: str) -> set[str]:
    """Parse a comma-separated roles string into a lowercase set.

    Example: ``"admin,auditor"`` → ``{"admin", "auditor"}``
    """
    if not roles_str:
        return set()
    return {r.strip().lower() for r in roles_str.split(",") if r.strip()}


def has_role(user, role: str) -> bool:
    """Return True if *user* has the given *role*."""
    if user is None:
        return False
    return role.lower() in _parse_roles(user.roles)


def has_any_role(user, *roles: str) -> bool:
    """Return True if *user* has at least one of the given *roles*."""
    if user is None:
        return False
    user_roles = _parse_roles(user.roles)
    return bool(user_roles & {r.lower() for r in roles})


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def login_required(f):
    """Decorator that ensures the user is authenticated.

    Redirects to the login page if ``g.current_user`` is ``None``.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.get("current_user") is None:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def roles_required(*roles):
    """Decorator that checks ``g.current_user`` has at least one of *roles*.

    If the user is not authenticated, redirects to the login page.
    If the user is authenticated but lacks the required role, returns 403.

    Usage::

        @app.route("/admin/users")
        @roles_required("admin")
        def admin_users():
            ...

        @app.route("/audits/new")
        @roles_required("auditor", "admin")
        def new_audit():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.get("current_user")

            # Not authenticated → redirect to login
            if user is None:
                return redirect(url_for("auth.login"))

            # Check if user has at least one of the required roles
            # Admin always has full access (Req 2.6)
            if has_any_role(user, *roles) or has_role(user, "admin"):
                return f(*args, **kwargs)

            # Insufficient role → 403 Forbidden (Req 2.7)
            abort(403)

        return decorated_function

    return decorator
