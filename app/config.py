"""Application configuration loaded from environment variables."""

import os

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    """Default configuration with sensible defaults, overridable via env vars."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

    # Database — store in instance/ so Docker volume mount persists it
    INSTANCE_DIR = os.path.join(basedir, "instance")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_DIR, 'totika.db')}"
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(basedir, "uploads")
    )
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB

    # Base path for reverse proxy sub-path deployment
    BASE_PATH = os.environ.get("BASE_PATH", "/")
    APPLICATION_ROOT = BASE_PATH

    # Session settings
    SESSION_EXPIRY_HOURS = int(os.environ.get("SESSION_EXPIRY_HOURS", "8"))
    INACTIVITY_TIMEOUT_MINUTES = int(
        os.environ.get("INACTIVITY_TIMEOUT_MINUTES", "30")
    )

    # Seed data directory
    SEED_DATA_DIR = os.environ.get(
        "SEED_DATA_DIR", os.path.join(basedir, "seed_data")
    )

    # Reverse proxy
    BEHIND_PROXY = os.environ.get("BEHIND_PROXY", "false").lower() == "true"

    # Default branding
    DEFAULT_COMPANY_NAME = "Tōtika Audit Tool"

    # Default admin account
    DEFAULT_ADMIN_PASSWORD = os.environ.get(
        "DEFAULT_ADMIN_PASSWORD", "admin"
    )

    # WebAuthn / Passkey settings
    WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
    WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Tōtika Audit Tool")
    WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:5000")


class TestConfig(Config):
    """Configuration for testing."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(basedir, "test_uploads")
    SEED_DATA_DIR = os.path.join(basedir, "test_seed_data")
