"""Authentication blueprint: login, logout, MFA, password reset."""

import logging
import random
import string
from datetime import datetime, timedelta

import pyotp
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import db
from app.models.user import User
from app.utils.auth import (
    SESSION_COOKIE_NAME,
    check_account_lockout,
    create_session,
    invalidate_session,
    record_failed_login,
    reset_failed_logins,
    verify_password,
)
from app.utils.logging import log_activity
from app.utils.proxy import get_client_ip, is_https

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

# Password reset token expiry: 1 hour
PASSWORD_RESET_MAX_AGE = 3600
PASSWORD_RESET_SALT = "password-reset-salt"

# Email MFA code expiry: 5 minutes
EMAIL_MFA_CODE_LENGTH = 6
EMAIL_MFA_CODE_EXPIRY_SECONDS = 300


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_serializer() -> URLSafeTimedSerializer:
    """Return an itsdangerous serializer using the app SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _generate_password_reset_token(user: User) -> str:
    """Generate a time-limited password reset token for *user*."""
    s = _get_serializer()
    return s.dumps(user.email, salt=PASSWORD_RESET_SALT)


def _verify_password_reset_token(token: str) -> str | None:
    """Verify a password reset token and return the email, or None if invalid/expired."""
    s = _get_serializer()
    try:
        email = s.loads(token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE)
        return email
    except (BadSignature, SignatureExpired):
        return None


def _generate_email_mfa_code() -> str:
    """Generate a random 6-digit numeric code for email MFA."""
    return "".join(random.choices(string.digits, k=EMAIL_MFA_CODE_LENGTH))


def _send_email_mfa_code(user: User, code: str) -> bool:
    """Send the MFA code via email. Returns True on success, False if mailer unavailable."""
    try:
        from app.services.mailer import send_email

        body = (
            f"Hello {user.display_name},\n\n"
            f"Your verification code is: {code}\n\n"
            f"This code expires in 5 minutes.\n"
            f"If you did not request this, please ignore this email."
        )
        return send_email(user.email, "Verification Code", body)
    except (ImportError, Exception) as exc:
        logger.warning("Could not send email MFA code to %s: %s", user.email, exc)
        return False


def _send_password_reset_email(user: User, reset_url: str) -> bool:
    """Send the password reset link via email. Returns True on success."""
    try:
        from app.services.mailer import send_email

        body = (
            f"Hello {user.display_name},\n\n"
            f"A password reset was requested for your account.\n\n"
            f"Click the link below to reset your password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour.\n"
            f"If you did not request this, please ignore this email."
        )
        return send_email(user.email, "Password Reset Request", body)
    except (ImportError, Exception) as exc:
        logger.warning("Could not send password reset email to %s: %s", user.email, exc)
        return False


def _set_session_cookie(response, token: str):
    """Set the session cookie on the response with appropriate flags.

    Cookie flags:
    - HttpOnly=True always (prevents JS access)
    - Secure=True when behind HTTPS (detected via proxy headers or direct)
    - SameSite=Lax (CSRF mitigation while allowing top-level navigations)
    """
    secure = is_https()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="Lax",
        max_age=current_app.config.get("SESSION_EXPIRY_HOURS", 8) * 3600,
    )
    return response


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login form (GET) and credential validation (POST)."""
    if request.method == "GET":
        return render_template("auth/login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Uniform error message for all credential failures (Req 1.2)
    error_msg = "Invalid username or password"

    # Look up user
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(error_msg, "error")
        return render_template("auth/login.html"), 401

    # Check if account is locked (Req 1.6)
    if check_account_lockout(user):
        remaining = user.locked_until - datetime.utcnow()
        minutes_left = max(1, int(remaining.total_seconds() / 60) + 1)
        flash(
            f"Account temporarily locked. Try again in {minutes_left} minutes.",
            "error",
        )
        return render_template("auth/login.html"), 403

    # Check if user is active
    if not user.is_active:
        flash(error_msg, "error")
        return render_template("auth/login.html"), 401

    # Verify password
    if not verify_password(user, password):
        record_failed_login(user)
        log_activity("login_failed", {"username": username}, user_id=user.id)
        db.session.commit()
        flash(error_msg, "error")
        return render_template("auth/login.html"), 401

    # Password correct — reset failed login counter
    reset_failed_logins(user)

    # Check if MFA is enabled (dual MFA support)
    mfa_methods = user.available_mfa_methods
    if mfa_methods:
        session["mfa_user_id"] = user.id
        session["mfa_available_methods"] = mfa_methods

        # Pick primary method: prefer TOTP, fall back to email
        primary = "totp" if "totp" in mfa_methods else "email"
        session["mfa_type"] = primary

        # For email MFA, generate and send code
        if primary == "email":
            code = _generate_email_mfa_code()
            session["mfa_email_code"] = code
            session["mfa_email_code_expires"] = (
                datetime.utcnow() + timedelta(seconds=EMAIL_MFA_CODE_EXPIRY_SECONDS)
            ).isoformat()
            _send_email_mfa_code(user, code)

        return redirect(url_for("auth.login_mfa"))

    # Legacy single mfa_type field (backward compat)
    if user.mfa_type in ("totp", "email") and not mfa_methods:
        session["mfa_user_id"] = user.id
        session["mfa_type"] = user.mfa_type
        session["mfa_available_methods"] = [user.mfa_type]

        if user.mfa_type == "email":
            code = _generate_email_mfa_code()
            session["mfa_email_code"] = code
            session["mfa_email_code_expires"] = (
                datetime.utcnow() + timedelta(seconds=EMAIL_MFA_CODE_EXPIRY_SECONDS)
            ).isoformat()
            _send_email_mfa_code(user, code)

        return redirect(url_for("auth.login_mfa"))

    # No MFA — issue session directly (Req 1.1)
    ip = get_client_ip()
    token = create_session(user, ip=ip)
    log_activity("login", {"username": user.username}, user_id=user.id, ip_address=ip)
    db.session.commit()
    response = make_response(redirect(url_for("audits.audit_list")))
    _set_session_cookie(response, token)
    return response


# ---------------------------------------------------------------------------
# MFA verification
# ---------------------------------------------------------------------------


@auth_bp.route("/login/mfa", methods=["GET", "POST"])
def login_mfa():
    """MFA code entry form (GET) and verification (POST)."""
    mfa_user_id = session.get("mfa_user_id")
    mfa_type = session.get("mfa_type")
    mfa_available = session.get("mfa_available_methods", [])

    if mfa_user_id is None or mfa_type is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, mfa_user_id)
    if user is None:
        session.pop("mfa_user_id", None)
        session.pop("mfa_type", None)
        return redirect(url_for("auth.login"))

    # Determine if user can switch methods
    can_switch = len(mfa_available) > 1
    other_method = None
    if can_switch:
        other_method = [m for m in mfa_available if m != mfa_type][0]

    if request.method == "GET":
        return render_template(
            "auth/mfa.html",
            mfa_type=mfa_type,
            can_switch=can_switch,
            other_method=other_method,
        )

    code = request.form.get("code", "").strip()
    error_msg = "Invalid verification code"

    if mfa_type == "totp":
        if not user.totp_secret:
            flash("MFA is not properly configured. Contact an administrator.", "error")
            return render_template(
                "auth/mfa.html", mfa_type=mfa_type, can_switch=can_switch, other_method=other_method
            ), 400

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            flash(error_msg, "error")
            return render_template(
                "auth/mfa.html", mfa_type=mfa_type, can_switch=can_switch, other_method=other_method
            ), 401

    elif mfa_type == "email":
        stored_code = session.get("mfa_email_code")
        expires_str = session.get("mfa_email_code_expires")

        if stored_code is None or expires_str is None:
            flash(error_msg, "error")
            return render_template(
                "auth/mfa.html", mfa_type=mfa_type, can_switch=can_switch, other_method=other_method
            ), 401

        expires = datetime.fromisoformat(expires_str)
        if datetime.utcnow() > expires:
            flash("Verification code has expired. Please log in again.", "error")
            _clear_mfa_session()
            return redirect(url_for("auth.login"))

        if code != stored_code:
            flash(error_msg, "error")
            return render_template(
                "auth/mfa.html", mfa_type=mfa_type, can_switch=can_switch, other_method=other_method
            ), 401

    else:
        flash("Unsupported MFA type.", "error")
        return redirect(url_for("auth.login"))

    # MFA verified — issue session
    _clear_mfa_session()

    ip = get_client_ip()
    token = create_session(user, ip=ip)
    log_activity("login", {"username": user.username}, user_id=user.id, ip_address=ip)
    db.session.commit()
    response = make_response(redirect(url_for("audits.audit_list")))
    _set_session_cookie(response, token)
    return response


@auth_bp.route("/login/mfa/switch", methods=["POST"])
def switch_mfa_method():
    """Switch to an alternative MFA method during login."""
    mfa_user_id = session.get("mfa_user_id")
    mfa_available = session.get("mfa_available_methods", [])

    if mfa_user_id is None or len(mfa_available) < 2:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, mfa_user_id)
    if user is None:
        _clear_mfa_session()
        return redirect(url_for("auth.login"))

    current_method = session.get("mfa_type")
    new_method = [m for m in mfa_available if m != current_method][0]
    session["mfa_type"] = new_method

    # If switching to email, generate and send a new code
    if new_method == "email":
        code = _generate_email_mfa_code()
        session["mfa_email_code"] = code
        session["mfa_email_code_expires"] = (
            datetime.utcnow() + timedelta(seconds=EMAIL_MFA_CODE_EXPIRY_SECONDS)
        ).isoformat()
        _send_email_mfa_code(user, code)
        flash("A verification code has been sent to your email.", "info")

    return redirect(url_for("auth.login_mfa"))


def _clear_mfa_session():
    """Remove all MFA-related keys from the Flask session."""
    for key in ("mfa_user_id", "mfa_type", "mfa_available_methods",
                "mfa_email_code", "mfa_email_code_expires"):
        session.pop(key, None)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Invalidate the current session and clear the cookie (Req 1.5, 19.2)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        invalidate_session(token)

    log_activity("logout")
    db.session.commit()

    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie(SESSION_COOKIE_NAME)
    flash("You have been logged out.", "info")
    return response


# ---------------------------------------------------------------------------
# Password reset request
# ---------------------------------------------------------------------------


@auth_bp.route("/password/reset", methods=["GET", "POST"])
def password_reset_request():
    """Password reset request form (GET) and email sending (POST) (Req 1.8)."""
    if request.method == "GET":
        return render_template("auth/reset_request.html")

    email = request.form.get("email", "").strip()

    # Always show the same message regardless of whether the email exists
    # to prevent user enumeration
    success_msg = (
        "If an account with that email exists, a password reset link has been sent."
    )

    user = User.query.filter_by(email=email).first()
    if user is not None and user.is_active:
        token = _generate_password_reset_token(user)
        # Use detected app base URL for correct domain behind reverse proxy
        from app.utils.proxy import get_app_base_url
        base = get_app_base_url()
        reset_path = url_for("auth.password_reset_confirm", token=token)
        reset_url = f"{base}{reset_path}"
        _send_password_reset_email(user, reset_url)

    flash(success_msg, "info")
    return render_template("auth/reset_request.html")


# ---------------------------------------------------------------------------
# Password reset confirmation
# ---------------------------------------------------------------------------


@auth_bp.route("/password/reset/<token>", methods=["GET", "POST"])
def password_reset_confirm(token):
    """Password reset form (GET) and new password submission (POST)."""
    email = _verify_password_reset_token(token)
    if email is None:
        flash("This reset link has expired or is invalid.", "error")
        return redirect(url_for("auth.password_reset_request"))

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("This reset link has expired or is invalid.", "error")
        return redirect(url_for("auth.password_reset_request"))

    if request.method == "GET":
        return render_template("auth/reset_form.html", token=token)

    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not password:
        flash("Password is required.", "error")
        return render_template("auth/reset_form.html", token=token), 400

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("auth/reset_form.html", token=token), 400

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("auth/reset_form.html", token=token), 400

    # Update password
    from app.utils.auth import hash_password

    user.password_hash = hash_password(password)
    user.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Your password has been reset. Please log in.", "success")
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Self-service password change (logged-in users)
# ---------------------------------------------------------------------------


@auth_bp.route("/password/change", methods=["GET", "POST"])
def change_password():
    """Allow logged-in users to change their own password."""
    from app.utils.auth import hash_password
    from app.utils.rbac import login_required as _login_required

    # Manual login check (can't use decorator easily here)
    if not hasattr(g, "current_user") or g.current_user is None:
        return redirect(url_for("auth.login"))

    user = g.current_user

    if request.method == "GET":
        return render_template("auth/change_password.html")

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not verify_password(user, current_password):
        flash("Current password is incorrect.", "error")
        return render_template("auth/change_password.html"), 400

    if not new_password:
        flash("New password is required.", "error")
        return render_template("auth/change_password.html"), 400

    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
        return render_template("auth/change_password.html"), 400

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("auth/change_password.html"), 400

    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Password changed successfully.", "success")
    return redirect(url_for("audits.audit_list"))
