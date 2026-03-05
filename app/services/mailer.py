"""SMTP mailer service — sends emails using configured SMTP settings.

All emails use the branding company name and auto-detected app URL.
Returns False if SMTP is not configured. All failures are handled gracefully.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_branding_name() -> str:
    """Return the configured company name from branding settings."""
    try:
        from app.extensions import db
        from app.models.settings import BrandingSettings

        row = db.session.get(BrandingSettings, 1)
        if row and row.company_name:
            return row.company_name
    except Exception:
        pass
    return "Tōtika Audit Tool"


def _get_branding_colour() -> str:
    """Return the primary brand colour."""
    try:
        from app.extensions import db
        from app.models.settings import BrandingSettings

        row = db.session.get(BrandingSettings, 1)
        if row and row.primary_colour:
            return row.primary_colour
    except Exception:
        pass
    return "#f97316"


def _wrap_html(body_text: str, company_name: str | None = None,
               colour: str | None = None) -> str:
    """Wrap plain-text body in a branded HTML email template."""
    name = company_name or _get_branding_name()
    clr = colour or _get_branding_colour()
    # Convert newlines to <br> for HTML
    html_body = body_text.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:2rem 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="padding:2rem 2rem 1rem;text-align:center;">
  <h1 style="margin:0;font-size:1.5rem;color:{clr};">{name}</h1>
</td></tr>
<tr><td style="padding:1rem 2rem 2rem;color:#e2e8f0;font-size:0.95rem;line-height:1.6;">
  {html_body}
</td></tr>
<tr><td style="padding:1rem 2rem;border-top:1px solid #334155;text-align:center;">
  <p style="margin:0;color:#64748b;font-size:0.8rem;">{name}</p>
</td></tr>
</table>
</td></tr></table>
</body></html>"""


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a branded email via configured SMTP settings.

    The subject line is prefixed with the branding company name.
    The body is wrapped in a branded HTML template.

    Returns True on success, False if SMTP is not configured or sending fails.
    """
    try:
        from app.extensions import db
        from app.models.settings import SMTPSettings
        from app.utils.encryption import decrypt_value

        smtp_settings = db.session.get(SMTPSettings, 1)
        if smtp_settings is None or not smtp_settings.host:
            logger.debug("SMTP not configured — skipping email to %s", to)
            return False

        # Decrypt password if present
        password = None
        if smtp_settings.password_encrypted:
            password = decrypt_value(smtp_settings.password_encrypted)
            if password is None:
                logger.warning(
                    "Failed to decrypt SMTP password — cannot send email to %s", to
                )
                return False

        company_name = _get_branding_name()
        colour = _get_branding_colour()

        # Build multipart message (HTML + plain text fallback)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{company_name} — {subject}"
        msg["From"] = smtp_settings.sender_address or ""
        msg["To"] = to

        # Plain text part
        msg.attach(MIMEText(body, "plain"))
        # HTML part
        msg.attach(MIMEText(
            _wrap_html(body, company_name, colour), "html"
        ))

        # Connect and send
        server = smtplib.SMTP(smtp_settings.host, smtp_settings.port, timeout=10)
        try:
            if smtp_settings.use_tls:
                server.starttls()
            if smtp_settings.username and password:
                server.login(smtp_settings.username, password)
            server.sendmail(msg["From"], [to], msg.as_string())
        finally:
            server.quit()

        logger.info("Email sent to=%s subject=%s", to, subject)
        return True

    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to, exc)
        return False
