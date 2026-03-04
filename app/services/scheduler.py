"""Scheduler service — reminder checks and overdue action marking.

Provides two callable functions:
- check_reminders(): sends email reminders for audits due within 14 days
- check_overdue_actions(): marks corrective actions past due date as Overdue

Both run on app startup and are exposed for cron integration.
"""

import logging
from datetime import date, timedelta

from app.extensions import db
from app.models.audit import Audit
from app.models.action import CorrectiveAction
from app.models.user import User
from app.services.mailer import send_email

logger = logging.getLogger(__name__)

REMINDER_DAYS = 14


def check_reminders():
    """Find audits with next_review_due within 14 days and send email reminders.

    Skips audits with status Completed or Archived.
    Skips if SMTP is not configured (send_email returns False).
    """
    today = date.today()
    threshold = today + timedelta(days=REMINDER_DAYS)

    audits = (
        Audit.query
        .filter(Audit.next_review_due.isnot(None))
        .filter(Audit.next_review_due <= threshold)
        .filter(Audit.next_review_due >= today)
        .filter(Audit.status.notin_(["Completed", "Archived"]))
        .all()
    )

    sent_count = 0
    for audit in audits:
        auditor = db.session.get(User, audit.auditor_id)
        if auditor is None or not auditor.email:
            logger.debug(
                "Skipping reminder for audit %d — no auditor or email.", audit.id
            )
            continue

        days_until = (audit.next_review_due - today).days
        subject = f"Audit Review Reminder — due in {days_until} day(s)"
        body = (
            f"Hello {auditor.display_name},\n\n"
            f"Audit #{audit.id} has a review due on {audit.next_review_due.isoformat()}.\n"
            f"That is {days_until} day(s) from today.\n\n"
            f"Please ensure the audit is completed on time.\n\n"
            f"— Tōtika Audit Tool"
        )

        if send_email(auditor.email, subject, body):
            sent_count += 1

    logger.info("Reminder check complete: %d reminder(s) sent.", sent_count)
    return sent_count


def check_overdue_actions():
    """Mark corrective actions past due date as Overdue.

    Only updates actions with status Open or In_Progress whose due_date
    is strictly before today.
    """
    today = date.today()

    overdue_actions = (
        CorrectiveAction.query
        .filter(CorrectiveAction.due_date.isnot(None))
        .filter(CorrectiveAction.due_date < today)
        .filter(CorrectiveAction.status.in_(["Open", "In_Progress"]))
        .all()
    )

    updated_count = 0
    for action in overdue_actions:
        action.status = "Overdue"
        updated_count += 1

        # Send overdue notification to assigned user (Req 7.7)
        if action.assigned_to_id:
            try:
                assigned_user = db.session.get(User, action.assigned_to_id)
                if assigned_user and assigned_user.email:
                    send_email(
                        to=assigned_user.email,
                        subject=f"Corrective Action Overdue — {action.criterion_code}",
                        body=(
                            f"Hello {assigned_user.display_name},\n\n"
                            f"A corrective action assigned to you is now overdue.\n\n"
                            f"Criterion: {action.criterion_code}\n"
                            f"Description: {action.description}\n"
                            f"Due date: {action.due_date.isoformat()}\n\n"
                            f"Please address this action as soon as possible.\n\n"
                            f"— Tōtika Audit Tool"
                        ),
                    )
            except Exception:
                pass  # Gracefully skip if email fails

    if updated_count > 0:
        db.session.commit()

    logger.info(
        "Overdue check complete: %d action(s) marked as Overdue.", updated_count
    )
    return updated_count
