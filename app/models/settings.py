"""Singleton settings models — BrandingSettings, SMTPSettings."""

from app.extensions import db


class BrandingSettings(db.Model):
    """Singleton (id=1) for company branding configuration."""

    __tablename__ = "branding_settings"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(
        db.String(200), default="Tōtika Audit Tool", nullable=False
    )
    logo_filename = db.Column(db.String(255), nullable=True)
    primary_colour = db.Column(db.String(7), default="#f97316", nullable=False)
    accent_colour = db.Column(db.String(7), default="#fb923c", nullable=False)
    header_bg_colour = db.Column(db.String(7), default="#0a0a23", nullable=False)
    header_text_colour = db.Column(db.String(7), default="#ffffff", nullable=False)
    footer_text = db.Column(db.String(500), default="", nullable=False)
    footer_bg_colour = db.Column(db.String(7), default="#0a0a23", nullable=False)
    footer_text_colour = db.Column(db.String(7), default="#94a3b8", nullable=False)

    def __repr__(self):
        return f"<BrandingSettings {self.company_name}>"


class SMTPSettings(db.Model):
    """Singleton (id=1) for SMTP email configuration."""

    __tablename__ = "smtp_settings"

    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(255), nullable=True)
    port = db.Column(db.Integer, default=587, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    password_encrypted = db.Column(db.Text, nullable=True)
    sender_address = db.Column(db.String(255), nullable=True)
    use_tls = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<SMTPSettings host={self.host}>"
