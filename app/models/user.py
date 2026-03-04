"""User, Session, and Passkey models."""

from datetime import datetime

from app.extensions import db


class User(db.Model):
    """Application user with role-based access and optional MFA."""

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    roles = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    mfa_type = db.Column(db.String(20), nullable=True)
    totp_secret = db.Column(db.String(64), nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    mfa_totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_email_enabled = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sessions = db.relationship("Session", backref="user", lazy="dynamic")
    passkeys = db.relationship("UserPasskey", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    audits_as_auditor = db.relationship(
        "Audit", foreign_keys="Audit.auditor_id", backref="auditor", lazy="dynamic"
    )
    audits_as_auditee = db.relationship(
        "Audit", foreign_keys="Audit.auditee_id", backref="auditee", lazy="dynamic"
    )
    activity_logs = db.relationship("ActivityLog", backref="user", lazy="dynamic")

    @property
    def has_dual_mfa(self) -> bool:
        """Return True if user has both TOTP and email MFA enabled."""
        return self.mfa_totp_enabled and self.mfa_email_enabled

    @property
    def available_mfa_methods(self) -> list[str]:
        """Return list of enabled MFA method names."""
        methods = []
        if self.mfa_totp_enabled:
            methods.append("totp")
        if self.mfa_email_enabled:
            methods.append("email")
        return methods

    def __repr__(self):
        return f"<User {self.username}>"


class UserPasskey(db.Model):
    """WebAuthn / Passkey credential for passwordless login."""

    __tablename__ = "user_passkey"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    credential_id = db.Column(db.Text, unique=True, nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, nullable=False, default=0)
    name = db.Column(db.String(100), nullable=False, default="My Passkey")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserPasskey {self.name} user_id={self.user_id}>"


class Session(db.Model):
    """Server-side session tracking with token hash."""

    __tablename__ = "session"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_active_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f"<Session user_id={self.user_id}>"
