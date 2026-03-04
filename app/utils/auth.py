"""Authentication utilities: password hashing, session management, account lockout."""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from flask import current_app, g, request, redirect, url_for

from app.extensions import db
from app.models.user import User, Session


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _truncate_password(password: str) -> bytes:
    """Encode and truncate a password to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12.

    Returns the bcrypt hash as a UTF-8 string suitable for DB storage.
    Passwords are truncated to 72 bytes (bcrypt's internal limit).
    """
    return bcrypt.hashpw(
        _truncate_password(password), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")


def verify_password(user: User, password: str) -> bool:
    """Verify a plaintext password against the user's stored bcrypt hash.

    Passwords are truncated to 72 bytes to match bcrypt's internal limit.
    """
    return bcrypt.checkpw(
        _truncate_password(password), user.password_hash.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# Session token management
# ---------------------------------------------------------------------------

def generate_session_token() -> str:
    """Generate a cryptographically secure session token with 256-bit entropy.

    Returns a 64-character hex string (32 bytes = 256 bits).
    """
    return secrets.token_hex(32)


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user: User, ip: str | None = None) -> str:
    """Create a new server-side session for *user*.

    Stores the SHA-256 hash of the token in the database.
    Returns the raw token (to be set as an HTTP-only cookie).
    """
    token = generate_session_token()
    expiry_hours = current_app.config.get("SESSION_EXPIRY_HOURS", 8)
    now = datetime.utcnow()

    session_record = Session(
        user_id=user.id,
        token_hash=_hash_token(token),
        created_at=now,
        expires_at=now + timedelta(hours=expiry_hours),
        last_active_at=now,
        ip_address=ip,
    )
    db.session.add(session_record)
    db.session.commit()
    return token


def validate_session(token: str) -> Session | None:
    """Validate a session token and return the Session record if valid.

    A session is valid when:
    - A matching token_hash exists in the DB
    - The session has not expired (expires_at > now)
    - The session has not been inactive for longer than the configured
      inactivity timeout (default 30 minutes)

    On success the session's ``last_active_at`` is bumped to *now*.
    Returns ``None`` when the token is invalid or the session has expired.
    """
    token_hash = _hash_token(token)
    session_record = Session.query.filter_by(token_hash=token_hash).first()
    if session_record is None:
        return None

    now = datetime.utcnow()

    # Check absolute expiry
    if now > session_record.expires_at:
        db.session.delete(session_record)
        db.session.commit()
        return None

    # Check inactivity timeout
    inactivity_minutes = current_app.config.get("INACTIVITY_TIMEOUT_MINUTES", 30)
    if now > session_record.last_active_at + timedelta(minutes=inactivity_minutes):
        db.session.delete(session_record)
        db.session.commit()
        return None

    # Session is valid — bump activity timestamp
    session_record.last_active_at = now
    db.session.commit()
    return session_record


def invalidate_session(token: str) -> None:
    """Invalidate a single session by its raw token."""
    token_hash = _hash_token(token)
    session_record = Session.query.filter_by(token_hash=token_hash).first()
    if session_record is not None:
        db.session.delete(session_record)
        db.session.commit()


def invalidate_all_sessions(user_id: int) -> None:
    """Invalidate every session belonging to *user_id*."""
    Session.query.filter_by(user_id=user_id).delete()
    db.session.commit()


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 15


def check_account_lockout(user: User) -> bool:
    """Return True if the account is currently locked out."""
    if user.locked_until is None:
        return False
    return datetime.utcnow() < user.locked_until


def record_failed_login(user: User) -> None:
    """Increment the failed-login counter and lock the account at the threshold."""
    user.failed_login_count += 1
    if user.failed_login_count >= LOCKOUT_THRESHOLD:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    db.session.commit()


def reset_failed_logins(user: User) -> None:
    """Reset the failed-login counter and clear any lockout (called on success)."""
    user.failed_login_count = 0
    user.locked_until = None
    db.session.commit()


# ---------------------------------------------------------------------------
# Session middleware (Flask before_request)
# ---------------------------------------------------------------------------

SESSION_COOKIE_NAME = "session_token"


def load_user_from_session():
    """Flask before_request handler: read session cookie, validate, attach user to g.

    Skips validation for static files and auth endpoints (login, password reset).
    Sets ``g.current_user`` to the authenticated User or ``None``.
    """
    g.current_user = None

    # Skip for static assets
    if request.path.startswith("/static"):
        return None

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        return None

    session_record = validate_session(token)
    if session_record is None:
        return None

    user = db.session.get(User, session_record.user_id)
    if user is None or not user.is_active:
        # User deleted or deactivated — kill the session
        invalidate_session(token)
        return None

    g.current_user = user
    return None
