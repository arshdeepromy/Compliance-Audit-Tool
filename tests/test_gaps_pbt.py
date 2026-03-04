"""Property-based tests for Gap Checklist and Corrective Actions.

Feature: totika-audit-webapp
Property 16: Gap checklist contains exactly criteria scored 0 or 1
Property 17: Corrective action lifecycle persistence
Property 34: Corrective action summary counts match actual statuses

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 7.1, 7.3, 7.4, 7.5, 7.6**
"""

import itertools
from datetime import date, datetime

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.action import CorrectiveAction
from app.models.audit import Audit, AuditScore
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACTION_STATUSES = ["Open", "In_Progress", "Completed", "Overdue"]
PRIORITIES = ["critical", "high", "medium"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = itertools.count()


def _uid():
    return next(_counter)


def _make_app(tmp_path):
    """Create a fresh Flask app with its own SQLite DB."""
    uid = _uid()

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'gaps_pbt_{uid}.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_user(app, roles="auditor,admin", username=None):
    """Create a user and return (user_id, token)."""
    uid = _uid()
    if username is None:
        username = f"user_{uid}"
    with app.app_context():
        user = User(
            username=username,
            email=f"{username}@example.com",
            display_name=username.title(),
            password_hash=hash_password("test-pw"),
            roles=roles,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user.id, token


def _make_template_with_n_criteria(app, n):
    """Create a template with *n* criteria (MB1..MBn) in one section."""
    with app.app_context():
        template = AuditTemplate(
            name=f"Template_{_uid()}", version="1.0", is_active=True
        )
        db.session.add(template)
        db.session.flush()

        section = TemplateSection(
            template_id=template.id, name="Section 1", sort_order=1
        )
        db.session.add(section)
        db.session.flush()

        codes = []
        for i in range(1, n + 1):
            code = f"MB{i}"
            codes.append(code)
            c = TemplateCriterion(
                section_id=section.id,
                code=code,
                title=f"Criterion {i}",
                sort_order=i,
                na_allowed=False,
            )
            db.session.add(c)

        db.session.commit()
        return template.id, codes


def _make_audit_with_scores(app, user_id, template_id, score_map):
    """Create an In_Progress audit with the given code→score mapping."""
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=user_id,
            status="In_Progress",
            audit_date=date(2026, 1, 15),
        )
        db.session.add(audit)
        db.session.flush()

        sections = TemplateSection.query.filter_by(template_id=template_id).all()
        for section in sections:
            criteria = TemplateCriterion.query.filter_by(
                section_id=section.id
            ).order_by(TemplateCriterion.sort_order).all()
            for criterion in criteria:
                score_val = score_map.get(criterion.code)
                s = AuditScore(
                    audit_id=audit.id,
                    criterion_id=criterion.id,
                    score=score_val,
                )
                db.session.add(s)

        db.session.commit()
        return audit.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for a list of scores (0–4) for N criteria (2–10)
st_score_list = st.integers(min_value=2, max_value=10).flatmap(
    lambda n: st.tuples(
        st.just(n),
        st.lists(st.integers(min_value=0, max_value=4), min_size=n, max_size=n),
    )
)

# Strategy for corrective action data
st_action_data = st.fixed_dictionaries({
    "description": st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=100,
    ).map(lambda s: s.strip()).filter(lambda s: len(s) > 0),
    "priority": st.sampled_from(PRIORITIES),
})

# Strategy for corrective action status
st_action_status = st.sampled_from(ACTION_STATUSES)

# Strategy for a set of corrective actions with various statuses
st_action_set = st.lists(
    st.tuples(st_action_status, st.sampled_from(PRIORITIES)),
    min_size=1,
    max_size=15,
)


# ---------------------------------------------------------------------------
# Property 16: Gap checklist contains exactly criteria scored 0 or 1
# ---------------------------------------------------------------------------


class TestProperty16GapChecklistContents:
    """**Validates: Requirements 7.1**

    For any set of criterion scores, the gap list should contain exactly
    those criteria with score 0 or 1.
    """

    @given(data=st_score_list)
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_gap_list_contains_exactly_low_scored_criteria(self, tmp_path, data):
        """Gap checklist contains exactly criteria scored 0 or 1."""
        n, scores = data
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, n)

        # Build score map
        score_map = {codes[i]: scores[i] for i in range(n)}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        # Expected gap codes: those with score 0 or 1
        expected_gap_codes = {
            code for code, score in score_map.items() if score in (0, 1)
        }

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.get(f"/audits/{audit_id}/gaps")
            assert resp.status_code == 200
            html = resp.data.decode()

        # Extract gap codes from the HTML using data-criterion-code attributes
        import re
        found_codes = set(re.findall(r'data-criterion-code="([^"]+)"', html))

        assert found_codes == expected_gap_codes, (
            f"Expected gap codes {expected_gap_codes}, found {found_codes}. "
            f"Score map: {score_map}"
        )

    @given(data=st_score_list)
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_gap_priority_matches_score(self, tmp_path, data):
        """Score 0 → critical priority, score 1 → high priority."""
        n, scores = data
        # Only run if there are gaps
        assume(any(s in (0, 1) for s in scores))

        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, n)
        score_map = {codes[i]: scores[i] for i in range(n)}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.get(f"/audits/{audit_id}/gaps")
            assert resp.status_code == 200
            html = resp.data.decode()

        # For each gap code, verify the priority badge
        for code, score in score_map.items():
            if score == 0:
                # Should have critical badge near this code
                assert f'data-criterion-code="{code}"' in html
                # Find the gap card and check for critical badge
                import re
                card_pattern = (
                    rf'data-criterion-code="{code}".*?(?=data-criterion-code="|$)'
                )
                card_match = re.search(card_pattern, html, re.DOTALL)
                if card_match:
                    card_html = card_match.group()
                    assert "badge-critical" in card_html, (
                        f"Score 0 criterion {code} should have critical badge"
                    )
            elif score == 1:
                assert f'data-criterion-code="{code}"' in html
                import re
                card_pattern = (
                    rf'data-criterion-code="{code}".*?(?=data-criterion-code="|$)'
                )
                card_match = re.search(card_pattern, html, re.DOTALL)
                if card_match:
                    card_html = card_match.group()
                    assert "badge-high" in card_html, (
                        f"Score 1 criterion {code} should have high badge"
                    )


# ---------------------------------------------------------------------------
# Property 17: Corrective action lifecycle persistence
# ---------------------------------------------------------------------------


class TestProperty17CorrectiveActionLifecycle:
    """**Validates: Requirements 7.3, 7.4, 7.5**

    Creating and updating corrective actions should persist all fields
    correctly. Completion records completed_at and completed_by.
    """

    @given(action_data=st_action_data)
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_create_action_persists_all_fields(self, tmp_path, action_data):
        """Creating a corrective action persists description, priority, and status."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, 3)
        score_map = {codes[0]: 0, codes[1]: 1, codes[2]: 3}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.post(
                f"/api/audits/{audit_id}/actions",
                json={
                    "criterion_code": codes[0],
                    "description": action_data["description"],
                    "priority": action_data["priority"],
                    "due_date": "2026-06-15",
                },
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["ok"] is True
            assert data["action"]["description"] == action_data["description"]
            assert data["action"]["priority"] == action_data["priority"]
            assert data["action"]["status"] == "Open"
            assert data["action"]["criterion_code"] == codes[0]
            assert data["action"]["due_date"] == "2026-06-15"

        # Verify in DB
        with app.app_context():
            action = CorrectiveAction.query.filter_by(audit_id=audit_id).first()
            assert action is not None
            assert action.description == action_data["description"]
            assert action.priority == action_data["priority"]
            assert action.status == "Open"
            assert action.due_date == date(2026, 6, 15)

    @given(new_status=st.sampled_from(["In_Progress", "Completed", "Overdue"]))
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_update_action_status_persists(self, tmp_path, new_status):
        """Updating a corrective action status persists correctly."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, 2)
        score_map = {codes[0]: 0, codes[1]: 3}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        # Create an action first
        with app.app_context():
            action = CorrectiveAction(
                audit_id=audit_id,
                criterion_code=codes[0],
                description="Test action",
                priority="critical",
                status="Open",
            )
            db.session.add(action)
            db.session.commit()
            action_id = action.id

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.put(
                f"/api/audits/{audit_id}/actions/{action_id}",
                json={"status": new_status},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["action"]["status"] == new_status

        # Verify in DB
        with app.app_context():
            action = db.session.get(CorrectiveAction, action_id)
            assert action.status == new_status

    @given(data=st.data())
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_completion_records_timestamp_and_user(self, tmp_path, data):
        """Marking an action as Completed records completed_at and completed_by_id."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, 2)
        score_map = {codes[0]: 0, codes[1]: 3}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        # Pick a starting status that is not Completed
        start_status = data.draw(st.sampled_from(["Open", "In_Progress", "Overdue"]))

        with app.app_context():
            action = CorrectiveAction(
                audit_id=audit_id,
                criterion_code=codes[0],
                description="Test completion",
                priority="critical",
                status=start_status,
            )
            db.session.add(action)
            db.session.commit()
            action_id = action.id

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.put(
                f"/api/audits/{audit_id}/actions/{action_id}",
                json={"status": "Completed"},
            )
            assert resp.status_code == 200
            data_resp = resp.get_json()
            assert data_resp["action"]["completed_at"] is not None
            assert data_resp["action"]["completed_by_id"] == user_id

        # Verify in DB
        with app.app_context():
            action = db.session.get(CorrectiveAction, action_id)
            assert action.completed_at is not None
            assert action.completed_by_id == user_id


# ---------------------------------------------------------------------------
# Property 34: Corrective action summary counts match actual statuses
# ---------------------------------------------------------------------------


class TestProperty34CorrectiveActionSummaryCounts:
    """**Validates: Requirements 7.6**

    The summary counts (total, open, in_progress, completed, overdue)
    should match the actual corrective action statuses.
    """

    @given(action_statuses=st_action_set)
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_summary_counts_match_actual_statuses(self, tmp_path, action_statuses):
        """Summary counts in the gaps page match the actual action status distribution."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes = _make_template_with_n_criteria(app, 3)
        # Ensure we have gap criteria to attach actions to
        score_map = {codes[0]: 0, codes[1]: 1, codes[2]: 3}
        audit_id = _make_audit_with_scores(app, user_id, template_id, score_map)

        # Create corrective actions with the generated statuses
        with app.app_context():
            for status, priority in action_statuses:
                # Distribute actions across gap criteria
                criterion_code = codes[0] if priority == "critical" else codes[1]
                action = CorrectiveAction(
                    audit_id=audit_id,
                    criterion_code=criterion_code,
                    description=f"Action {_uid()}",
                    priority=priority,
                    status=status,
                )
                if status == "Completed":
                    action.completed_at = datetime.utcnow()
                    action.completed_by_id = user_id
                db.session.add(action)
            db.session.commit()

        # Calculate expected counts
        expected_total = len(action_statuses)
        expected_open = sum(1 for s, _ in action_statuses if s == "Open")
        expected_in_progress = sum(1 for s, _ in action_statuses if s == "In_Progress")
        expected_completed = sum(1 for s, _ in action_statuses if s == "Completed")
        expected_overdue = sum(1 for s, _ in action_statuses if s == "Overdue")

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")
            resp = client.get(f"/audits/{audit_id}/gaps")
            assert resp.status_code == 200
            html = resp.data.decode()

        # Verify summary counts in the HTML
        assert f"Total: {expected_total}" in html, (
            f"Expected Total: {expected_total} in HTML"
        )
        assert f"Open: {expected_open}" in html, (
            f"Expected Open: {expected_open} in HTML"
        )
        assert f"In Progress: {expected_in_progress}" in html, (
            f"Expected In Progress: {expected_in_progress} in HTML"
        )
        assert f"Completed: {expected_completed}" in html, (
            f"Expected Completed: {expected_completed} in HTML"
        )
        assert f"Overdue: {expected_overdue}" in html, (
            f"Expected Overdue: {expected_overdue} in HTML"
        )
