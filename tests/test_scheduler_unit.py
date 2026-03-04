"""Unit tests for the scheduler service — reminders and overdue actions."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models.audit import Audit
from app.models.action import CorrectiveAction
from app.models.user import User
from app.models.template import AuditTemplate, TemplateSection, TemplateCriterion
from app.services.scheduler import check_reminders, check_overdue_actions, REMINDER_DAYS
from app.utils.auth import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_template(session):
    """Create a minimal audit template and return it."""
    tpl = AuditTemplate(
        name="Test Template",
        version="1.0",
        is_active=True,
        is_builtin=False,
    )
    session.add(tpl)
    session.flush()
    section = TemplateSection(template_id=tpl.id, name="S1", sort_order=0)
    session.add(section)
    session.flush()
    crit = TemplateCriterion(
        section_id=section.id, code="T1", title="Test", sort_order=0
    )
    session.add(crit)
    session.flush()
    return tpl


def _create_auditor(session, username="auditor1", email="auditor1@example.com"):
    """Create and return an auditor user."""
    user = User(
        username=username,
        email=email,
        display_name="Auditor One",
        password_hash=hash_password("password123"),
        roles="auditor",
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def _create_audit(session, template, auditor, next_review_due=None, status="Draft"):
    """Create and return an audit."""
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        status=status,
        next_review_due=next_review_due,
    )
    session.add(audit)
    session.flush()
    return audit


def _create_action(session, audit, status="Open", due_date=None):
    """Create and return a corrective action."""
    action = CorrectiveAction(
        audit_id=audit.id,
        criterion_code="T1",
        description="Fix this",
        priority="high",
        status=status,
        due_date=due_date,
    )
    session.add(action)
    session.flush()
    return action


# ---------------------------------------------------------------------------
# check_overdue_actions tests
# ---------------------------------------------------------------------------

class TestCheckOverdueActions:
    """Tests for check_overdue_actions()."""

    def test_marks_open_past_due_as_overdue(self, app, db_session):
        """Open action past due date should be marked Overdue."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        yesterday = date.today() - timedelta(days=1)
        action = _create_action(db_session, audit, status="Open", due_date=yesterday)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Overdue"
        assert count == 1

    def test_marks_in_progress_past_due_as_overdue(self, app, db_session):
        """In_Progress action past due date should be marked Overdue."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        yesterday = date.today() - timedelta(days=1)
        action = _create_action(db_session, audit, status="In_Progress", due_date=yesterday)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Overdue"
        assert count == 1

    def test_does_not_mark_completed_as_overdue(self, app, db_session):
        """Completed actions should not be changed even if past due."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        yesterday = date.today() - timedelta(days=1)
        action = _create_action(db_session, audit, status="Completed", due_date=yesterday)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Completed"
        assert count == 0

    def test_does_not_mark_already_overdue(self, app, db_session):
        """Already Overdue actions should not be counted again."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        yesterday = date.today() - timedelta(days=1)
        action = _create_action(db_session, audit, status="Overdue", due_date=yesterday)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Overdue"
        assert count == 0

    def test_does_not_mark_future_due_date(self, app, db_session):
        """Actions with future due dates should not be marked Overdue."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        tomorrow = date.today() + timedelta(days=1)
        action = _create_action(db_session, audit, status="Open", due_date=tomorrow)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Open"
        assert count == 0

    def test_does_not_mark_action_due_today(self, app, db_session):
        """Actions due today should NOT be marked Overdue (only strictly past)."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        action = _create_action(db_session, audit, status="Open", due_date=date.today())
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Open"
        assert count == 0

    def test_no_due_date_not_marked(self, app, db_session):
        """Actions without a due date should not be marked Overdue."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        action = _create_action(db_session, audit, status="Open", due_date=None)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(action)
        assert action.status == "Open"
        assert count == 0

    def test_multiple_actions_mixed(self, app, db_session):
        """Multiple actions: only eligible ones should be marked Overdue."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        audit = _create_audit(db_session, tpl, auditor)
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        a1 = _create_action(db_session, audit, status="Open", due_date=yesterday)
        a2 = _create_action(db_session, audit, status="In_Progress", due_date=yesterday)
        a3 = _create_action(db_session, audit, status="Completed", due_date=yesterday)
        a4 = _create_action(db_session, audit, status="Open", due_date=tomorrow)
        db_session.commit()

        count = check_overdue_actions()

        db_session.refresh(a1)
        db_session.refresh(a2)
        db_session.refresh(a3)
        db_session.refresh(a4)
        assert a1.status == "Overdue"
        assert a2.status == "Overdue"
        assert a3.status == "Completed"
        assert a4.status == "Open"
        assert count == 2


# ---------------------------------------------------------------------------
# check_reminders tests
# ---------------------------------------------------------------------------

class TestCheckReminders:
    """Tests for check_reminders()."""

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_sends_reminder_for_audit_due_within_14_days(self, mock_send, app, db_session):
        """Audit due within 14 days should trigger a reminder email."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=7)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 1
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == auditor.email
        assert "Reminder" in call_args[0][1]

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_sends_reminder_for_audit_due_today(self, mock_send, app, db_session):
        """Audit due today should trigger a reminder."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        _create_audit(db_session, tpl, auditor, next_review_due=date.today(), status="In_Progress")
        db_session.commit()

        count = check_reminders()

        assert count == 1
        mock_send.assert_called_once()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_sends_reminder_for_audit_due_in_exactly_14_days(self, mock_send, app, db_session):
        """Audit due in exactly 14 days should trigger a reminder."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=REMINDER_DAYS)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 1
        mock_send.assert_called_once()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_no_reminder_for_audit_due_beyond_14_days(self, mock_send, app, db_session):
        """Audit due more than 14 days away should not trigger a reminder."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=REMINDER_DAYS + 1)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_not_called()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_no_reminder_for_completed_audit(self, mock_send, app, db_session):
        """Completed audits should not trigger reminders."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=5)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Completed")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_not_called()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_no_reminder_for_archived_audit(self, mock_send, app, db_session):
        """Archived audits should not trigger reminders."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=5)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Archived")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_not_called()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_no_reminder_for_past_due_date(self, mock_send, app, db_session):
        """Audits with past due dates should not trigger reminders."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        past = date.today() - timedelta(days=1)
        _create_audit(db_session, tpl, auditor, next_review_due=past, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_not_called()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_no_reminder_when_no_due_date(self, mock_send, app, db_session):
        """Audits without a next_review_due should not trigger reminders."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        _create_audit(db_session, tpl, auditor, next_review_due=None, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_not_called()

    @patch("app.services.scheduler.send_email", return_value=False)
    def test_smtp_not_configured_returns_zero(self, mock_send, app, db_session):
        """When SMTP is not configured (send_email returns False), count is 0."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=5)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Draft")
        db_session.commit()

        count = check_reminders()

        assert count == 0
        mock_send.assert_called_once()

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_multiple_audits_multiple_reminders(self, mock_send, app, db_session):
        """Multiple eligible audits should each get a reminder."""
        tpl = _create_template(db_session)
        a1 = _create_auditor(db_session, username="aud1", email="aud1@example.com")
        a2 = _create_auditor(db_session, username="aud2", email="aud2@example.com")
        due = date.today() + timedelta(days=3)
        _create_audit(db_session, tpl, a1, next_review_due=due, status="Draft")
        _create_audit(db_session, tpl, a2, next_review_due=due, status="In_Progress")
        db_session.commit()

        count = check_reminders()

        assert count == 2
        assert mock_send.call_count == 2

    @patch("app.services.scheduler.send_email", return_value=True)
    def test_review_status_gets_reminder(self, mock_send, app, db_session):
        """Audits in Review status should still get reminders."""
        tpl = _create_template(db_session)
        auditor = _create_auditor(db_session)
        due = date.today() + timedelta(days=5)
        _create_audit(db_session, tpl, auditor, next_review_due=due, status="Review")
        db_session.commit()

        count = check_reminders()

        assert count == 1
        mock_send.assert_called_once()
