"""Proxy and base-path helpers for reverse-proxy deployments.

Provides utilities to:
- Detect whether the current request is over HTTPS (via X-Forwarded-Proto or direct)
- Retrieve the real client IP (via X-Forwarded-For or remote_addr)
- Check if the app is running behind a reverse proxy

These helpers work in conjunction with Flask's ProxyFix middleware (applied in
the app factory when BEHIND_PROXY=True) and the APPLICATION_ROOT config that
is set from BASE_PATH.
"""

from flask import current_app, request


def is_https() -> bool:
    """Return True if the current request is over HTTPS.

    Checks ``request.scheme`` which, when ProxyFix is active, already
    reflects the value of the X-Forwarded-Proto header.  Falls back to
    inspecting the header directly for cases where ProxyFix is not enabled
    but the header is still present.
    """
    if request.scheme == "https":
        return True
    # Fallback: check the raw header even without ProxyFix
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    return forwarded_proto.lower() == "https"


def get_client_ip() -> str:
    """Return the real client IP address.

    When ProxyFix is active ``request.remote_addr`` already contains the
    correct value from X-Forwarded-For.  As a safety net we also inspect
    the header directly.
    """
    # ProxyFix rewrites remote_addr, so this is usually correct
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For may contain a chain: "client, proxy1, proxy2"
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def get_base_path() -> str:
    """Return the configured base URL path prefix (e.g. ``/audit/``).

    Defaults to ``/`` when not configured.
    """
    return current_app.config.get("BASE_PATH", "/")
