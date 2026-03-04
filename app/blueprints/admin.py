"""Admin panel blueprint — branding, SMTP, user management, activity log.

Routes:
    GET/POST /admin/branding    — company branding settings
    GET/POST /admin/smtp        — SMTP configuration
    POST     /admin/smtp/test   — send test email
    GET      /admin/users       — user list
    GET/POST /admin/users/new   — create user
    GET/POST /admin/users/<id>  — edit user
    GET      /admin/logs        — activity log viewer
"""

import os
import secrets
import smtplib
import string
import uuid
from email.mime.text import MIMEText

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.extensions import db
from app.models.log import ActivityLog
from app.models.settings import BrandingSettings, SMTPSettings
from app.models.user import User
from app.utils.auth import hash_password, invalidate_all_sessions
from app.utils.encryption import decrypt_value, encrypt_value
from app.utils.logging import log_activity
from app.utils.rbac import roles_required

admin_bp = Blueprint("admin", __name__)

# Allowed image extensions for logo upload
ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg"}


@admin_bp.before_request
def _set_admin_page():
    """Automatically set admin_page context for the admin nav highlight."""
    from flask import g as _g
    endpoint = request.endpoint or ""
    if "branding" in endpoint:
        _g.admin_page = "branding"
    elif "smtp" in endpoint:
        _g.admin_page = "smtp"
    elif "user" in endpoint:
        _g.admin_page = "users"
    elif "log" in endpoint:
        _g.admin_page = "logs"
    elif "import" in endpoint:
        _g.admin_page = "import"
    else:
        _g.admin_page = ""


@admin_bp.app_context_processor
def _inject_admin_page():
    """Make admin_page available in all admin templates."""
    return {"admin_page": getattr(g, "admin_page", "")}


def _allowed_logo(filename: str) -> bool:
    """Return True if the filename has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


# ---------------------------------------------------------------------------
# Branding settings
# ---------------------------------------------------------------------------


@admin_bp.route("/admin/branding", methods=["GET", "POST"])
@roles_required("admin")
def branding():
    """View and update company branding settings."""
    branding_row = db.session.get(BrandingSettings, 1)

    # Ensure singleton exists (should be seeded on startup, but be safe)
    if branding_row is None:
        branding_row = BrandingSettings(
            id=1,
            company_name="Tōtika Audit Tool",
            primary_colour="#f97316",
            accent_colour="#fb923c",
        )
        db.session.add(branding_row)
        db.session.commit()

    if request.method == "GET":
        return render_template("admin/branding.html", branding=branding_row)

    # --- POST: update branding ---
    company_name = request.form.get("company_name", "").strip()
    primary_colour = request.form.get("primary_colour", "").strip()
    accent_colour = request.form.get("accent_colour", "").strip()

    if company_name:
        branding_row.company_name = company_name
    if primary_colour:
        branding_row.primary_colour = primary_colour
    if accent_colour:
        branding_row.accent_colour = accent_colour

    # Handle logo upload
    if "logo" in request.files:
        file = request.files["logo"]
        if file.filename and file.filename != "":
            if not _allowed_logo(file.filename):
                flash(
                    "Logo must be a PNG, JPG, or JPEG image.",
                    "error",
                )
                return render_template(
                    "admin/branding.html", branding=branding_row
                ), 400

            # Save the logo file
            ext = file.filename.rsplit(".", 1)[1].lower()
            unique_filename = f"logo_{uuid.uuid4().hex}.{ext}"
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, unique_filename)
            file.save(filepath)

            # Remove old logo file if it exists
            if branding_row.logo_filename:
                old_path = os.path.join(
                    upload_folder, branding_row.logo_filename
                )
                if os.path.exists(old_path):
                    os.remove(old_path)

            branding_row.logo_filename = unique_filename

    db.session.commit()
    log_activity("settings_change", {"setting": "branding"})
    db.session.commit()
    flash("Branding settings updated.", "success")
    return redirect(url_for("admin.branding"))


# ---------------------------------------------------------------------------
# SMTP settings
# ---------------------------------------------------------------------------


def _get_smtp_settings() -> SMTPSettings:
    """Return the SMTP singleton, creating it if needed."""
    smtp = db.session.get(SMTPSettings, 1)
    if smtp is None:
        smtp = SMTPSettings(id=1)
        db.session.add(smtp)
        db.session.commit()
    return smtp


def smtp_is_configured(smtp: SMTPSettings) -> bool:
    """Return True if SMTP has the minimum required fields set."""
    return bool(smtp.host and smtp.sender_address)


@admin_bp.route("/admin/smtp", methods=["GET", "POST"])
@roles_required("admin")
def smtp():
    """View and update SMTP configuration."""
    smtp_row = _get_smtp_settings()

    if request.method == "GET":
        return render_template(
            "admin/smtp.html",
            smtp=smtp_row,
            smtp_configured=smtp_is_configured(smtp_row),
            password_set=bool(smtp_row.password_encrypted),
        )

    # --- POST: save SMTP settings ---
    host = request.form.get("host", "").strip()
    port_str = request.form.get("port", "587").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")  # Don't strip — may be intentional
    sender_address = request.form.get("sender_address", "").strip()
    use_tls = request.form.get("use_tls") == "on"

    # Validate port
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            raise ValueError
    except (ValueError, TypeError):
        flash("Port must be a number between 1 and 65535.", "error")
        return render_template(
            "admin/smtp.html",
            smtp=smtp_row,
            smtp_configured=smtp_is_configured(smtp_row),
            password_set=bool(smtp_row.password_encrypted),
        ), 400

    smtp_row.host = host or None
    smtp_row.port = port
    smtp_row.username = username or None
    smtp_row.sender_address = sender_address or None
    smtp_row.use_tls = use_tls

    # Only update password if a new one was provided
    if password:
        smtp_row.password_encrypted = encrypt_value(password)

    db.session.commit()
    log_activity("settings_change", {"setting": "smtp"})
    db.session.commit()
    flash("SMTP settings saved.", "success")
    return redirect(url_for("admin.smtp"))


@admin_bp.route("/admin/smtp/test", methods=["POST"])
@roles_required("admin")
def smtp_test():
    """Send a test email using the current SMTP configuration."""
    smtp_row = _get_smtp_settings()

    if not smtp_is_configured(smtp_row):
        flash("SMTP is not configured. Please save settings first.", "error")
        return redirect(url_for("admin.smtp"))

    # Determine recipient — use form input or fall back to sender address
    recipient = (request.form.get("test_recipient", "").strip()
                 or smtp_row.sender_address)

    # Decrypt password if set
    password = None
    if smtp_row.password_encrypted:
        password = decrypt_value(smtp_row.password_encrypted)
        if password is None:
            flash(
                "Failed to decrypt SMTP password. Please re-enter it.",
                "error",
            )
            return redirect(url_for("admin.smtp"))

    try:
        msg = MIMEText(
            "This is a test email from the Tōtika Audit Tool.\n\n"
            "If you received this message, your SMTP settings are working correctly."
        )
        msg["Subject"] = "Tōtika Audit Tool — SMTP Test"
        msg["From"] = smtp_row.sender_address
        msg["To"] = recipient

        if smtp_row.use_tls:
            server = smtplib.SMTP(smtp_row.host, smtp_row.port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_row.host, smtp_row.port, timeout=10)

        if smtp_row.username and password:
            server.login(smtp_row.username, password)

        server.sendmail(smtp_row.sender_address, [recipient], msg.as_string())
        server.quit()

        flash(f"Test email sent successfully to {recipient}.", "success")
    except Exception as exc:
        flash(f"Failed to send test email: {exc}", "error")

    return redirect(url_for("admin.smtp"))


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

VALID_ROLES = {"admin", "auditor", "auditee", "viewer"}


def _generate_temp_password(length: int = 12) -> str:
    """Generate a random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _validate_user_form(form, is_create: bool = True, existing_user: User | None = None):
    """Validate user creation/edit form data. Returns (errors, cleaned_data)."""
    errors = []
    username = form.get("username", "").strip()
    email = form.get("email", "").strip()
    display_name = form.get("display_name", "").strip()
    password = form.get("password", "")
    roles_list = form.getlist("roles")

    if is_create:
        if not username:
            errors.append("Username is required.")
        if not password:
            errors.append("Password is required.")

    if not email:
        errors.append("Email is required.")
    if not display_name:
        errors.append("Display name is required.")
    if not roles_list:
        errors.append("At least one role is required.")

    # Validate role values
    invalid_roles = [r for r in roles_list if r.lower() not in VALID_ROLES]
    if invalid_roles:
        errors.append(f"Invalid roles: {', '.join(invalid_roles)}")

    # Check uniqueness
    if is_create and username:
        if User.query.filter_by(username=username).first():
            errors.append(f"Username '{username}' is already taken.")
    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and (existing_user is None or existing_email.id != existing_user.id):
            errors.append(f"Email '{email}' is already in use.")
    if is_create and username:
        # Also check username uniqueness for create
        pass  # Already checked above

    cleaned = {
        "username": username,
        "email": email,
        "display_name": display_name,
        "password": password,
        "roles": ",".join(r.lower() for r in roles_list),
    }
    return errors, cleaned


@admin_bp.route("/admin/users", methods=["GET"])
@roles_required("admin")
def users_list():
    """Display all users."""
    users = User.query.order_by(User.username).all()
    return render_template("admin/users_list.html", users=users)


@admin_bp.route("/admin/users/new", methods=["GET", "POST"])
@roles_required("admin")
def user_create():
    """Create a new user account."""
    if request.method == "GET":
        return render_template(
            "admin/user_form.html",
            user=None,
            valid_roles=sorted(VALID_ROLES),
            mode="create",
        )

    errors, cleaned = _validate_user_form(request.form, is_create=True)
    if errors:
        for err in errors:
            flash(err, "error")
        return render_template(
            "admin/user_form.html",
            user=None,
            valid_roles=sorted(VALID_ROLES),
            mode="create",
        ), 400

    user = User(
        username=cleaned["username"],
        email=cleaned["email"],
        display_name=cleaned["display_name"],
        password_hash=hash_password(cleaned["password"]),
        roles=cleaned["roles"],
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()

    log_activity("user_create", {"username": user.username, "roles": user.roles})
    db.session.commit()

    flash(f"User '{user.username}' created successfully.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/admin/users/<int:id>", methods=["GET", "POST"])
@roles_required("admin")
def user_edit(id):
    """Edit an existing user account."""
    user = db.session.get(User, id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.users_list"))

    if request.method == "GET":
        return render_template(
            "admin/user_form.html",
            user=user,
            valid_roles=sorted(VALID_ROLES),
            mode="edit",
        )

    # Determine which action is being taken
    action = request.form.get("action", "save")

    if action == "deactivate":
        user.is_active = False
        invalidate_all_sessions(user.id)
        db.session.commit()
        log_activity("user_edit", {"username": user.username, "action": "deactivate"})
        db.session.commit()
        flash(f"User '{user.username}' has been deactivated.", "success")
        return redirect(url_for("admin.user_edit", id=user.id))

    if action == "activate":
        user.is_active = True
        db.session.commit()
        log_activity("user_edit", {"username": user.username, "action": "activate"})
        db.session.commit()
        flash(f"User '{user.username}' has been activated.", "success")
        return redirect(url_for("admin.user_edit", id=user.id))

    if action == "reset_password":
        temp_password = _generate_temp_password()
        user.password_hash = hash_password(temp_password)
        invalidate_all_sessions(user.id)
        db.session.commit()

        # Try to email the temporary password
        email_sent = _try_email_temp_password(user, temp_password)
        if email_sent:
            flash(
                f"Password reset. Temporary password sent to {user.email}.",
                "success",
            )
        else:
            flash(
                f"Password reset. Temporary password: {temp_password}",
                "success",
            )
        return redirect(url_for("admin.user_edit", id=user.id))

    # Default action: save edits
    errors, cleaned = _validate_user_form(
        request.form, is_create=False, existing_user=user
    )
    if errors:
        for err in errors:
            flash(err, "error")
        return render_template(
            "admin/user_form.html",
            user=user,
            valid_roles=sorted(VALID_ROLES),
            mode="edit",
        ), 400

    user.display_name = cleaned["display_name"]
    user.email = cleaned["email"]
    user.roles = cleaned["roles"]

    # MFA settings — dual MFA support
    mfa_action = request.form.get("mfa_action", "")

    if mfa_action == "enable_totp":
        # Enable TOTP — generate secret if needed
        if not user.totp_secret:
            import pyotp
            user.totp_secret = pyotp.random_base32()
        user.mfa_totp_enabled = True
        # Keep legacy field in sync
        if not user.mfa_email_enabled:
            user.mfa_type = "totp"
        else:
            user.mfa_type = "totp"  # primary

    elif mfa_action == "disable_totp":
        user.mfa_totp_enabled = False
        user.totp_secret = None
        if user.mfa_email_enabled:
            user.mfa_type = "email"
        else:
            user.mfa_type = None

    elif mfa_action == "enable_email":
        # Email MFA requires verified email
        if not user.email_verified:
            flash("Email must be verified before enabling email MFA.", "error")
            return render_template(
                "admin/user_form.html",
                user=user,
                valid_roles=sorted(VALID_ROLES),
                mode="edit",
            ), 400
        user.mfa_email_enabled = True
        if not user.mfa_totp_enabled:
            user.mfa_type = "email"

    elif mfa_action == "disable_email":
        user.mfa_email_enabled = False
        if user.mfa_totp_enabled:
            user.mfa_type = "totp"
        else:
            user.mfa_type = None

    else:
        # Legacy dropdown fallback (no mfa_action)
        mfa_type = request.form.get("mfa_type", "").strip() or None
        if mfa_type and mfa_type not in ("totp", "email"):
            mfa_type = None
        if mfa_type == "totp" and not user.totp_secret:
            import pyotp
            user.totp_secret = pyotp.random_base32()
        if mfa_type != "totp":
            user.totp_secret = None
        user.mfa_type = mfa_type

    # Optional password change
    if cleaned["password"]:
        user.password_hash = hash_password(cleaned["password"])

    db.session.commit()
    log_activity("user_edit", {"username": user.username})
    db.session.commit()
    flash(f"User '{user.username}' updated.", "success")
    return redirect(url_for("admin.users_list"))


def _try_email_temp_password(user: User, temp_password: str) -> bool:
    """Attempt to email a temporary password to the user. Returns True on success."""
    smtp_row = _get_smtp_settings()
    if not smtp_is_configured(smtp_row):
        return False

    password = None
    if smtp_row.password_encrypted:
        password = decrypt_value(smtp_row.password_encrypted)
        if password is None:
            return False

    try:
        msg = MIMEText(
            f"Your password has been reset.\n\n"
            f"Temporary password: {temp_password}\n\n"
            f"Please log in and change your password as soon as possible."
        )
        msg["Subject"] = "Tōtika Audit Tool — Password Reset"
        msg["From"] = smtp_row.sender_address
        msg["To"] = user.email

        if smtp_row.use_tls:
            server = smtplib.SMTP(smtp_row.host, smtp_row.port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(smtp_row.host, smtp_row.port, timeout=10)

        if smtp_row.username and password:
            server.login(smtp_row.username, password)

        server.sendmail(smtp_row.sender_address, [user.email], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Email verification for MFA setup
# ---------------------------------------------------------------------------


@admin_bp.route("/admin/users/<int:id>/send-verification", methods=["POST"])
@roles_required("admin")
def send_email_verification(id):
    """Send a verification code to the user's email address."""
    import random
    import string
    from datetime import datetime, timedelta

    user = db.session.get(User, id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.users_list"))

    if not user.email:
        flash("User has no email address.", "error")
        return redirect(url_for("admin.user_edit", id=id))

    # Generate 6-digit code
    code = "".join(random.choices(string.digits, k=6))

    # Store in Flask session (keyed by user id)
    from flask import session as flask_session
    flask_session[f"email_verify_code_{id}"] = code
    flask_session[f"email_verify_expires_{id}"] = (
        datetime.utcnow() + timedelta(minutes=10)
    ).isoformat()

    # Send the code
    try:
        from app.services.mailer import send_email
        send_email(
            user.email,
            "Email Verification Code",
            f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
        )
        flash(f"Verification code sent to {user.email}.", "success")
    except Exception as exc:
        flash(f"Failed to send verification email: {exc}", "error")

    return redirect(url_for("admin.user_edit", id=id))


@admin_bp.route("/admin/users/<int:id>/verify-email", methods=["POST"])
@roles_required("admin")
def verify_email(id):
    """Verify the email code and mark user's email as verified."""
    from datetime import datetime
    from flask import session as flask_session

    user = db.session.get(User, id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("admin.users_list"))

    code = request.form.get("verification_code", "").strip()
    stored_code = flask_session.get(f"email_verify_code_{id}")
    expires_str = flask_session.get(f"email_verify_expires_{id}")

    if not stored_code or not expires_str:
        flash("No verification code pending. Please send a new one.", "error")
        return redirect(url_for("admin.user_edit", id=id))

    expires = datetime.fromisoformat(expires_str)
    if datetime.utcnow() > expires:
        flask_session.pop(f"email_verify_code_{id}", None)
        flask_session.pop(f"email_verify_expires_{id}", None)
        flash("Verification code has expired. Please send a new one.", "error")
        return redirect(url_for("admin.user_edit", id=id))

    if code != stored_code:
        flash("Invalid verification code.", "error")
        return redirect(url_for("admin.user_edit", id=id))

    # Success — mark email as verified
    user.email_verified = True
    db.session.commit()

    flask_session.pop(f"email_verify_code_{id}", None)
    flask_session.pop(f"email_verify_expires_{id}", None)

    flash("Email verified successfully. You can now enable email MFA.", "success")
    return redirect(url_for("admin.user_edit", id=id))


# ---------------------------------------------------------------------------
# Activity log viewer (Req 15.1, 15.2, 15.3, 15.4)
# ---------------------------------------------------------------------------

# Canonical list of action types for the filter dropdown
ACTION_TYPES = [
    "login",
    "login_failed",
    "logout",
    "score_change",
    "audit_status_change",
    "user_create",
    "user_edit",
    "settings_change",
    "import",
]


@admin_bp.route("/admin/logs", methods=["GET"])
@roles_required("admin")
def activity_logs():
    """Display activity log entries in reverse chronological order.

    Supports filtering by:
    - ``user_id`` — specific user
    - ``action`` — action type
    - ``date_from`` / ``date_to`` — date range (inclusive)
    """
    from datetime import datetime as dt

    query = ActivityLog.query

    # --- Filters ---
    filter_user_id = request.args.get("user_id", "").strip()
    filter_action = request.args.get("action", "").strip()
    date_from_str = request.args.get("date_from", "").strip()
    date_to_str = request.args.get("date_to", "").strip()

    if filter_user_id:
        try:
            query = query.filter(ActivityLog.user_id == int(filter_user_id))
        except (ValueError, TypeError):
            pass

    if filter_action:
        query = query.filter(ActivityLog.action == filter_action)

    if date_from_str:
        try:
            date_from = dt.strptime(date_from_str, "%Y-%m-%d")
            query = query.filter(ActivityLog.created_at >= date_from)
        except ValueError:
            pass

    if date_to_str:
        try:
            # Include the entire "to" day
            date_to = dt.strptime(date_to_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(ActivityLog.created_at <= date_to)
        except ValueError:
            pass

    # Reverse chronological (Req 15.2)
    logs = query.order_by(ActivityLog.created_at.desc()).all()

    # Data for filter dropdowns
    users = User.query.order_by(User.username).all()

    return render_template(
        "admin/logs.html",
        logs=logs,
        users=users,
        action_types=ACTION_TYPES,
        filter_user_id=filter_user_id,
        filter_action=filter_action,
        date_from=date_from_str,
        date_to=date_to_str,
    )


# ---------------------------------------------------------------------------
# Bulk JSON import (Req 17.1, 17.2, 17.8)
# ---------------------------------------------------------------------------


@admin_bp.route("/admin/import", methods=["GET", "POST"])
@roles_required("admin")
def import_legacy():
    """Bulk import of legacy JSON files with preview."""
    import json

    if request.method == "GET":
        return render_template("admin/import.html", preview=None, errors=None)

    # --- POST: handle file upload ---
    if "json_file" not in request.files:
        flash("No file selected.", "error")
        return render_template("admin/import.html", preview=None, errors=None), 400

    file = request.files["json_file"]
    if not file.filename or file.filename == "":
        flash("No file selected.", "error")
        return render_template("admin/import.html", preview=None, errors=None), 400

    # Read and parse JSON
    try:
        raw = file.read().decode("utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        flash(f"Invalid JSON file: {exc}", "error")
        return render_template("admin/import.html", preview=None, errors=None), 400

    from app.services.importer import validate_legacy_json

    errors = validate_legacy_json(data)

    # Check if this is a preview or confirm action
    action = request.form.get("action", "preview")

    if action == "preview" or errors:
        # Show preview of the data
        meta = data.get("meta", {})
        scores = data.get("scores", {})
        gap_items = data.get("gapItems", [])
        preview = {
            "filename": file.filename,
            "assessor": meta.get("assessor", ""),
            "auditee": meta.get("auditee", ""),
            "date": meta.get("date", ""),
            "period": meta.get("period", ""),
            "next_review": meta.get("nextReview", ""),
            "score_count": len(scores),
            "gap_count": len(gap_items) if isinstance(gap_items, list) else 0,
            "raw_json": raw,
        }
        if errors:
            return render_template(
                "admin/import.html", preview=preview, errors=errors
            ), 400
        return render_template(
            "admin/import.html", preview=preview, errors=None
        )

    # --- Confirm import ---
    # On confirm, the raw JSON may come from the hidden field instead of file
    raw_json_field = request.form.get("raw_json", "")
    if raw_json_field:
        try:
            data = json.loads(raw_json_field)
        except json.JSONDecodeError:
            flash("Failed to parse stored JSON data.", "error")
            return render_template("admin/import.html", preview=None, errors=None), 400

    from app.services.importer import import_legacy_json

    source_name = file.filename if file.filename else "admin-import"
    try:
        audit = import_legacy_json(
            data,
            g.current_user.id,
            source_filename=source_name,
            status="Completed",
        )
    except Exception as exc:
        flash(f"Import failed: {exc}", "error")
        return render_template("admin/import.html", preview=None, errors=None), 500

    log_activity("import", {
        "audit_id": audit.id,
        "source": file.filename,
        "type": "admin-bulk",
    })
    db.session.commit()

    flash(
        f"Successfully imported '{file.filename}' as audit #{audit.id}.",
        "success",
    )
    return redirect(url_for("admin.import_legacy"))
