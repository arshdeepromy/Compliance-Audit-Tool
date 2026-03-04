"""SMTP mailer service — sends emails using configured SMTP settings.

Returns False if SMTP is not configured. All failures are handled gracefully.
"""

import logging
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via configured SMTP settings.

    Reads SMTP host, port, username, encrypted password, sender address,
    and TLS flag from the SMTPSettings singleton (id=1).  Decrypts the
    password using :func:`app.utils.encryption.decrypt_value`.

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

        # Build the message
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_settings.sender_address or ""
        msg["To"] = to

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
