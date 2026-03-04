"""Tōtika Audit Web Application — Flask app factory."""

import os

from flask import Flask

from .config import Config
from .extensions import db, init_db


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

    # Set APPLICATION_ROOT from BASE_PATH so url_for() respects the prefix
    base_path = app.config.get("BASE_PATH", "/")
    if base_path and base_path != "/":
        app.config["APPLICATION_ROOT"] = base_path

    # Ensure instance and upload folders exist
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialise database with WAL mode
    init_db(app)

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(audits_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

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
            }
        }

    return app
