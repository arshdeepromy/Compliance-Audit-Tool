"""Tōtika Audit Web Application — Flask app factory."""

import logging
import os

from flask import Flask

from .config import Config
from .extensions import db, init_db

logger = logging.getLogger(__name__)


def create_app(config_class=None, run_startup=True):
    """Create and configure the Flask application.

    Args:
        config_class: Configuration class to use. Defaults to Config.
        run_startup: Whether to run migrations and seed data on startup.
                     Set to False for testing or when migrations should be
                     handled separately.
    """
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # Warn if SECRET_KEY is still the default (OWASP A07: Security Misconfiguration)
    if app.config.get("SECRET_KEY") == "change-me-in-production" and not app.config.get("TESTING"):
        logger.warning(
            "⚠️  SECRET_KEY is set to the default value. "
            "Set a strong SECRET_KEY environment variable in production!"
        )

    # Set APPLICATION_ROOT from BASE_PATH so url_for() respects the prefix
    base_path = app.config.get("BASE_PATH", "/")
    if base_path and base_path != "/":
        app.config["APPLICATION_ROOT"] = base_path

    # Ensure instance and upload folders exist on the host
    instance_dir = os.path.join(app.root_path, "..", "instance")
    os.makedirs(instance_dir, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "backups"), exist_ok=True)

    # Initialise database with WAL mode
    init_db(app)

    # ── CSRF Protection (OWASP A01: Broken Access Control) ────────────
    from flask_wtf.csrf import CSRFProtect

    csrf = CSRFProtect(app)

    # Exempt the JSON API blueprint from CSRF (uses session auth + SameSite cookies)
    # API endpoints accept JSON bodies, not form submissions
    from .blueprints.api import api_bp as _api_bp
    csrf.exempt(_api_bp)

    # ── Rate Limiting (OWASP A07: Security Misconfiguration) ──────────
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],  # No global limit — apply per-route
        storage_uri="memory://",
    )
    # Store on app so blueprints can access it
    app.limiter = limiter

    # ── Security Headers (OWASP A05: Security Misconfiguration) ───────
    @app.after_request
    def set_security_headers(response):
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy — disable unnecessary browser features
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Content Security Policy — allow self + Google Fonts + CDN scripts
        if "text/html" in response.content_type:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "frame-ancestors 'self';"
            )
        # HSTS — only when behind HTTPS
        if app.config.get("BEHIND_PROXY", False):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # Apply ProxyFix middleware for reverse proxy support
    if app.config.get("BEHIND_PROXY", False):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    # Run migrations and seed default data
    if run_startup:
        from .startup import run_startup_tasks

        run_startup_tasks(app)

    # Register session middleware (before_request)
    from .utils.auth import load_user_from_session

    app.before_request(load_user_from_session)

    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.audits import audits_bp
    from .blueprints.templates import templates_bp
    from .blueprints.api import api_bp
    from .blueprints.admin import admin_bp
    from .blueprints.risks import risks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(risks_bp)

    # ── Apply rate limits to sensitive endpoints ─────────────────────
    # Auth blueprint: 10 requests/minute per IP (login, MFA, password reset)
    limiter.limit("10/minute")(auth_bp)

    # Root redirect — send / to login (or audits if already authenticated)
    from flask import redirect, url_for, g, send_from_directory

    @app.route("/")
    def index():
        if hasattr(g, "current_user") and g.current_user:
            return redirect(url_for("audits.audit_list"))
        return redirect(url_for("auth.login"))

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        """Serve uploaded files (logos, attachments)."""
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # Inject branding into Jinja2 context (loads from DB if available)
    @app.context_processor
    def inject_branding():
        from .models.settings import BrandingSettings

        branding_row = db.session.get(BrandingSettings, 1)
        if branding_row:
            return {
                "branding": {
                    "company_name": branding_row.company_name,
                    "primary_colour": branding_row.primary_colour,
                    "accent_colour": branding_row.accent_colour,
                    "logo_filename": branding_row.logo_filename,
                    "header_bg_colour": branding_row.header_bg_colour,
                    "header_text_colour": branding_row.header_text_colour,
                    "footer_text": branding_row.footer_text,
                    "footer_bg_colour": branding_row.footer_bg_colour,
                    "footer_text_colour": branding_row.footer_text_colour,
                }
            }
        return {
            "branding": {
                "company_name": app.config.get(
                    "DEFAULT_COMPANY_NAME", "Tōtika Audit Tool"
                ),
                "primary_colour": "#f97316",
                "accent_colour": "#fb923c",
                "logo_filename": None,
                "header_bg_colour": "#0a0a23",
                "header_text_colour": "#ffffff",
                "footer_text": "",
                "footer_bg_colour": "#0a0a23",
                "footer_text_colour": "#94a3b8",
            }
        }

    return app
