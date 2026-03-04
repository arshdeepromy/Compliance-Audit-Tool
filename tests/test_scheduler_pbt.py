"""Property-based tests for scheduling and activity logging.

Feature: totika-audit-webapp
Property 27: Audit reminders based on due date proximity
Property 28: Activity log records all significant actions with required fields

Uses Hypothesis for property-based testing with the Flask test client.
"""

import json
from datetime import date, timedelta, datetime
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app.extensions import db
from app.models.audit import Audit
from app.models.action import CorrectiveAction
from app.models.log import ActivityLog
from app.models.user import User
from app.models.template import AuditTemplate
from app.services.scheduler import check_reminders, REMINDER_DAYS
from app.utils.auth import hash_password
from app.utils.logging import log_activity


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Audit statuses
_ACTIVE_STATUSES = ["Draft", "In_Progress", "Review"]
_INACTIVE_STATUSES = ["Completed", "Archived"]

# Action strings for activity logging
_action_st = st.sampled_from([
    "login", "logout", "score_change", "audit_status_change",
    "user_creation", "user_edit", "settings_change", "import",
])

# Details: can be a string, dict, or list
_details_string_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=0,
    max_size=200,
)

_details_dict_st = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=20,
    ),
    values=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=0,
        max_size=50,
    ),
    min_size=0,
    max_size=5,
)

_details_list_st = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=0,
        max_size=50,
    ),
    min_size=0,
    max_size=5,
)

# IP addresses
_ip_address_st = st.from_regex(
    r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", fullmatch=True
)

# Suppress the function-scoped fixture health check
_suppress_fixture_check = settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _next_id():
    """Return a monotonically increasing integer for unique names."""
    global _counter
    _counter += 1
    return _counter


def _create_template(db_session):
    """Create a minimal audit template and return it."""
    tmpl = AuditTemplate(name=f"Test Template {_next_id()}", version="1.0", is_active=True)
    db_session.add(tmpl)
    db_session.flush()
    return tmpl


def _create_user(db_session):
    """Create a user with a unique username/email and return it."""
    n = _next_id()
    user = User(
        username=f"auditor_sched_{n}",
        email=f"auditor_sched_{n}@example.com",
        display_name="Scheduler Test User",
        password_hash=hash_password("test-pw-123"),
        roles="auditor",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


# ===========================================================================
# Property 27: Audit reminders based on due date proximity
# ===========================================================================


class TestProperty27AuditReminders:
    """Property 27: Audit reminders based on due date proximity.

    *For any* audit with a next_review_due date:
    - If due date is within 14 days from today AND status is not
      Completed/Archived → reminder should be sent
    - If due date is more than 14 days away → no reminder
    - If due date is in the past → no reminder
    - If status is Completed or Archived → no reminder

    **Validates: Requirements 14.1, 14.2, 14.4**
    """

    @_suppress_fixture_check
    @given(day_offset=st.integers(min_value=0, max_value=REMINDER_DAYS))
    def test_audit_within_reminder_window_sends_email(self, app, day_offset):
        """Audits with next_review_due within 0..14 days and active status
        should trigger a reminder email."""
        with app.app_context():
            template = _create_template(db.session)
            user = _create_user(db.session)
            due_date = date.today() + timedelta(days=day_offset)

            audit = Audit(
                template_id=template.id,
                auditor_id=user.id,
                status="In_Progress",
                next_review_due=due_date,
            )
            db.session.add(audit)
            db.session.commit()

            with patch("app.services.scheduler.send_email", return_value=True) as mock_send:
                sent = check_reminders()

                assert sent >= 1
                mock_send.assert_called()
                # Verify the email was sent to the auditor
                call_args = mock_send.call_args
                assert call_args[0][0] == user.email

    @_suppress_fixture_check
    @given(day_offset=st.integers(min_value=REMINDER_DAYS + 1, max_value=365))
    def test_audit_beyond_reminder_window_no_email(self, app, day_offset):
        """Audits with next_review_due more than 14 days away should NOT
        trigger a reminder."""
        with app.app_context():
            template = _create_template(db.session)
            user = _create_user(db.session)
            due_date = date.today() + timedelta(days=day_offset)

            audit = Audit(
                template_id=template.id,
                auditor_id=user.id,
                status="In_Progress",
                next_review_due=due_date,
            )
            db.session.add(audit)
            db.session.commit()

            with patch("app.services.scheduler.send_email", return_value=True) as mock_send:
                sent = check_reminders()

                assert sent == 0
                mock_send.assert_not_called()

    @_suppress_fixture_check
    @given(day_offset=st.integers(min_value=-365, max_value=-1))
    def test_audit_past_due_no_reminder(self, app, day_offset):
        """Audits with next_review_due in the past should NOT trigger a
        reminder."""
        with app.app_context():
            template = _create_template(db.session)
            user = _create_user(db.session)
            due_date = date.today() + timedelta(days=day_offset)

            audit = Audit(
                template_id=template.id,
                auditor_id=user.id,
                status="In_Progress",
                next_review_due=due_date,
            )
            db.session.add(audit)
            db.session.commit()

            with patch("app.services.scheduler.send_email", return_value=True) as mock_send:
                sent = check_reminders()

                assert sent == 0
                mock_send.assert_not_called()

    @_suppress_fixture_check
    @given(
        status=st.sampled_from(_INACTIVE_STATUSES),
        day_offset=st.integers(min_value=0, max_value=REMINDER_DAYS),
    )
    def test_completed_archived_audit_no_reminder(self, app, status, day_offset):
        """Audits with Completed or Archived status should NOT trigger
        reminders even if within the reminder window."""
        with app.app_context():
            template = _create_template(db.session)
            user = _create_user(db.session)
            due_date = date.today() + timedelta(days=day_offset)

            audit = Audit(
                template_id=template.id,
                auditor_id=user.id,
                status=status,
                next_review_due=due_date,
            )
            db.session.add(audit)
            db.session.commit()

            with patch("app.services.scheduler.send_email", return_value=True) as mock_send:
                sent = check_reminders()

                assert sent == 0
                mock_send.assert_not_called()

    @_suppress_fixture_check
    @given(status=st.sampled_from(_ACTIVE_STATUSES))
    def test_active_status_within_window_sends_reminder(self, app, status):
        """Any active status (Draft, In_Progress, Review) within the window
        should trigger a reminder."""
        with app.app_context():
            template = _create_template(db.session)
            user = _create_user(db.session)
            due_date = date.today() + timedelta(days=7)

            audit = Audit(
                template_id=template.id,
                auditor_id=user.id,
                status=status,
                next_review_due=due_date,
            )
            db.session.add(audit)
            db.session.commit()

            with patch("app.services.scheduler.send_email", return_value=True) as mock_send:
                sent = check_reminders()

                assert sent >= 1
                mock_send.assert_called()


# ===========================================================================
# Property 28: Activity log records all significant actions with required fields
# ===========================================================================


class TestProperty28ActivityLogRequiredFields:
    """Property 28: Activity log records all significant actions with required fields.

    *For any* significant action: log_activity(action, details, user_id,
    ip_address) creates an ActivityLog record with the correct action,
    details, user_id, ip_address, and a non-null created_at.

    If details is a dict/list, it's serialized to JSON string.

    **Validates: Requirements 15.1, 15.2, 15.4**
    """

    @_suppress_fixture_check
    @given(action=_action_st, details=_details_string_st, ip_address=_ip_address_st)
    def test_log_activity_persists_string_details(
        self, app, action, details, ip_address
    ):
        """log_activity with string details persists all required fields."""
        with app.app_context():
            user = _create_user(db.session)

            entry = log_activity(
                action=action,
                details=details,
                user_id=user.id,
                ip_address=ip_address,
            )
            db.session.commit()

            loaded = db.session.get(ActivityLog, entry.id)
            assert loaded is not None
            assert loaded.action == action
            assert loaded.user_id == user.id
            assert loaded.ip_address == ip_address
            assert loaded.created_at is not None
            # String details stored via str()
            if details:
                assert loaded.details == str(details)

    @_suppress_fixture_check
    @given(action=_action_st, details=_details_dict_st, ip_address=_ip_address_st)
    def test_log_activity_serializes_dict_details(
        self, app, action, details, ip_address
    ):
        """log_activity with dict details serializes to JSON string."""
        with app.app_context():
            user = _create_user(db.session)

            entry = log_activity(
                action=action,
                details=details,
                user_id=user.id,
                ip_address=ip_address,
            )
            db.session.commit()

            loaded = db.session.get(ActivityLog, entry.id)
            assert loaded is not None
            assert loaded.action == action
            assert loaded.user_id == user.id
            assert loaded.ip_address == ip_address
            assert loaded.created_at is not None
            # Dict should be serialized to JSON
            parsed = json.loads(loaded.details)
            assert parsed == details

    @_suppress_fixture_check
    @given(action=_action_st, details=_details_list_st, ip_address=_ip_address_st)
    def test_log_activity_serializes_list_details(
        self, app, action, details, ip_address
    ):
        """log_activity with list details serializes to JSON string."""
        with app.app_context():
            user = _create_user(db.session)

            entry = log_activity(
                action=action,
                details=details,
                user_id=user.id,
                ip_address=ip_address,
            )
            db.session.commit()

            loaded = db.session.get(ActivityLog, entry.id)
            assert loaded is not None
            assert loaded.action == action
            assert loaded.user_id == user.id
            assert loaded.ip_address == ip_address
            assert loaded.created_at is not None
            parsed = json.loads(loaded.details)
            assert parsed == details

    @_suppress_fixture_check
    @given(action=_action_st, ip_address=_ip_address_st)
    def test_log_activity_none_details(self, app, action, ip_address):
        """log_activity with None details stores None."""
        with app.app_context():
            user = _create_user(db.session)

            entry = log_activity(
                action=action,
                details=None,
                user_id=user.id,
                ip_address=ip_address,
            )
            db.session.commit()

            loaded = db.session.get(ActivityLog, entry.id)
            assert loaded is not None
            assert loaded.action == action
            assert loaded.user_id == user.id
            assert loaded.ip_address == ip_address
            assert loaded.created_at is not None
            assert loaded.details is None

    @_suppress_fixture_check
    @given(action=_action_st)
    def test_log_activity_created_at_is_recent(self, app, action):
        """The created_at timestamp should be close to now."""
        with app.app_context():
            user = _create_user(db.session)

            before = datetime.utcnow()
            entry = log_activity(
                action=action,
                details="test",
                user_id=user.id,
                ip_address="127.0.0.1",
            )
            db.session.commit()
            after = datetime.utcnow()

            loaded = db.session.get(ActivityLog, entry.id)
            assert loaded.created_at >= before
            assert loaded.created_at <= after

    def test_log_entries_reverse_chronological(self, app):
        """Activity log entries should be retrievable in reverse
        chronological order."""
        with app.app_context():
            user = _create_user(db.session)

            actions = ["login", "score_change", "logout"]
            for action_name in actions:
                log_activity(
                    action=action_name,
                    details=f"detail for {action_name}",
                    user_id=user.id,
                    ip_address="127.0.0.1",
                )
                db.session.commit()

            entries = (
                ActivityLog.query
                .order_by(ActivityLog.created_at.desc())
                .all()
            )
            assert len(entries) >= 3
            for i in range(len(entries) - 1):
                assert entries[i].created_at >= entries[i + 1].created_at
