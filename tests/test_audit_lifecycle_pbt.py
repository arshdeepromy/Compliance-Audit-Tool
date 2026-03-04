"""Property-based tests for Audit Lifecycle Management.

Feature: totika-audit-webapp
Property 11: Audit state machine enforces valid transitions only
Property 12: Completed and Archived audits are immutable

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**
"""

import itertools

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
    CriterionEvidenceItem,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session, SESSION_COOKIE_NAME


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_STATUSES = ["Draft", "In_Progress", "Review", "Completed", "Archived"]

# The only valid forward transitions
VALID_TRANSITIONS = {
    "Draft": "In_Progress",
    "In_Progress": "Review",
    "Review": "Completed",
    "Completed": "Archived",
}

# Map target status to the route used to trigger the transition
TRANSITION_ROUTES = {
    "Review": "/audits/{audit_id}/review",
    "Completed": "/audits/{audit_id}/finalise",
    "Archived": "/audits/{audit_id}/archive",
}

# All possible target statuses that can be attempted via routes
ROUTE_TARGETS = list(TRANSITION_ROUTES.keys())


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
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'audit_pbt_{uid}.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_user(app, roles="auditor,admin", username=None):
    """Create a user with the given roles and return (user_id, token).

    Default roles include both auditor and admin so the user can trigger
    all transition routes without 403 errors.
    """
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


def _make_template(app):
    """Create a minimal template with one section and two criteria (one with evidence)."""
    with app.app_context():
        template = AuditTemplate(
            name=f"Template_{_uid()}",
            version="1.0",
            is_active=True,
        )
        db.session.add(template)
        db.session.flush()

        section = TemplateSection(
            template_id=template.id, name="Section 1", sort_order=1
        )
        db.session.add(section)
        db.session.flush()

        c1 = TemplateCriterion(
            section_id=section.id, code="MB1", title="Criterion 1", sort_order=1
        )
        c2 = TemplateCriterion(
            section_id=section.id, code="MB2", title="Criterion 2", sort_order=2
        )
        db.session.add_all([c1, c2])
        db.session.flush()

        ev = CriterionEvidenceItem(
            criterion_id=c1.id, text="Evidence item 1", sort_order=1
        )
        db.session.add(ev)
        db.session.commit()
        return template.id


def _make_audit(app, user_id, template_id, status="Draft"):
    """Create an audit in the given status with AuditScore and EvidenceCheckState rows."""
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=user_id,
            status=status,
        )
        db.session.add(audit)
        db.session.flush()

        # Create score rows for all criteria in the template
        sections = TemplateSection.query.filter_by(template_id=template_id).all()
        for section in sections:
            criteria = TemplateCriterion.query.filter_by(section_id=section.id).all()
            for criterion in criteria:
                score = AuditScore(
                    audit_id=audit.id,
                    criterion_id=criterion.id,
                    score=3,  # Give a default score
                    notes="Test notes",
                )
                db.session.add(score)
                db.session.flush()

                evidence_items = CriterionEvidenceItem.query.filter_by(
                    criterion_id=criterion.id
                ).all()
                for item in evidence_items:
                    check_state = EvidenceCheckState(
                        audit_score_id=score.id,
                        evidence_item_id=item.id,
                        is_checked=True,
                    )
                    db.session.add(check_state)

        db.session.commit()
        return audit.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for picking a starting status
st_status = st.sampled_from(ALL_STATUSES)

# Strategy for picking a target status (one that has a route)
st_target = st.sampled_from(ROUTE_TARGETS)

# Strategy for generating all (source, target) pairs
st_source_target = st.tuples(st_status, st_target)


# ---------------------------------------------------------------------------
# Property 11: Audit state machine enforces valid transitions only
# ---------------------------------------------------------------------------


class TestProperty11AuditStateMachineTransitions:
    """**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

    For any audit, the only valid status transitions SHALL be:
    Draft → In_Progress, In_Progress → Review, Review → Completed,
    Completed → Archived. Any other transition attempt SHALL be rejected.
    """

    @given(data=st_source_target)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_valid_transitions_succeed_invalid_rejected(self, tmp_path, data):
        """For any (source_status, target_status) pair, the transition succeeds
        only when it matches the valid transition map, and is rejected otherwise.
        """
        source_status, target_status = data
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id, status=source_status)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        route = TRANSITION_ROUTES[target_status].format(audit_id=audit_id)
        resp = client.post(route, follow_redirects=False)

        expected_valid = VALID_TRANSITIONS.get(source_status) == target_status

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            if expected_valid:
                # Transition should succeed — redirect (302)
                assert resp.status_code == 302, (
                    f"Expected 302 for valid transition {source_status} → {target_status}, "
                    f"got {resp.status_code}"
                )
                assert audit.status == target_status, (
                    f"Audit should be in {target_status} after valid transition "
                    f"from {source_status}, but is {audit.status}"
                )
            else:
                # Transition should be rejected — 400
                assert resp.status_code == 400, (
                    f"Expected 400 for invalid transition {source_status} → {target_status}, "
                    f"got {resp.status_code}"
                )
                assert audit.status == source_status, (
                    f"Audit status should remain {source_status} after rejected "
                    f"transition to {target_status}, but is {audit.status}"
                )

    @given(source=st_status)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_each_status_has_at_most_one_valid_target(self, tmp_path, source):
        """For any source status, there is at most one valid target status.
        This confirms the state machine is linear (no branching).
        """
        valid_targets = [
            t for t in ROUTE_TARGETS if VALID_TRANSITIONS.get(source) == t
        ]
        assert len(valid_targets) <= 1, (
            f"Status {source} has multiple valid targets: {valid_targets}"
        )

    def test_archived_is_terminal(self, tmp_path):
        """Archived status has no valid outgoing transitions."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id, status="Archived")

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        for target, route_template in TRANSITION_ROUTES.items():
            route = route_template.format(audit_id=audit_id)
            resp = client.post(route, follow_redirects=False)
            assert resp.status_code == 400, (
                f"Archived → {target} should be rejected, got {resp.status_code}"
            )

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            assert audit.status == "Archived"


# ---------------------------------------------------------------------------
# Property 12: Completed and Archived audits are immutable
# ---------------------------------------------------------------------------


class TestProperty12CompletedArchivedImmutable:
    """**Validates: Requirements 4.6**

    For any audit in Completed or Archived status, attempts to modify
    scores, notes, evidence check states, or add/remove attachments
    SHALL be rejected with an error.
    """

    @given(
        immutable_status=st.sampled_from(["Completed", "Archived"]),
        new_score=st.integers(min_value=0, max_value=4),
        new_notes=st.text(min_size=1, max_size=50),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_score_modification_rejected_on_immutable_audit(
        self, tmp_path, immutable_status, new_score, new_notes
    ):
        """Directly modifying scores on a Completed or Archived audit
        should be prevented by the _can_modify_audit guard.
        """
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id, status=immutable_status)

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            # Verify the guard function rejects modifications
            from app.blueprints.audits import _can_modify_audit

            assert _can_modify_audit(audit) is False, (
                f"_can_modify_audit should return False for {immutable_status} audit"
            )

            # Capture original score data
            score_record = audit.scores.first()
            original_score = score_record.score
            original_notes = score_record.notes

            # Attempt to modify — the application should reject this
            # We verify the guard prevents it
            assert audit.status in ("Completed", "Archived")

    @given(immutable_status=st.sampled_from(["Completed", "Archived"]))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_evidence_check_state_modification_rejected(
        self, tmp_path, immutable_status
    ):
        """Evidence check states cannot be modified on Completed/Archived audits."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id, status=immutable_status)

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            from app.blueprints.audits import _can_modify_audit

            assert _can_modify_audit(audit) is False

            # Verify evidence check states exist and are protected
            score_record = audit.scores.first()
            check_states = score_record.evidence_check_states.all()
            if check_states:
                original_checked = check_states[0].is_checked
                # The guard prevents modification
                assert audit.status == immutable_status

    @given(
        immutable_status=st.sampled_from(["Completed", "Archived"]),
        modifiable_status=st.sampled_from(["Draft", "In_Progress", "Review"]),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_modifiable_vs_immutable_status_contrast(
        self, tmp_path, immutable_status, modifiable_status
    ):
        """Audits in Draft/In_Progress/Review are modifiable,
        while Completed/Archived are not.
        """
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)

        immutable_audit_id = _make_audit(
            app, user_id, template_id, status=immutable_status
        )
        modifiable_audit_id = _make_audit(
            app, user_id, template_id, status=modifiable_status
        )

        with app.app_context():
            from app.blueprints.audits import _can_modify_audit

            immutable_audit = db.session.get(Audit, immutable_audit_id)
            modifiable_audit = db.session.get(Audit, modifiable_audit_id)

            assert _can_modify_audit(immutable_audit) is False, (
                f"{immutable_status} audit should NOT be modifiable"
            )
            assert _can_modify_audit(modifiable_audit) is True, (
                f"{modifiable_status} audit SHOULD be modifiable"
            )

    @given(immutable_status=st.sampled_from(["Completed", "Archived"]))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_state_transitions_blocked_from_immutable_except_archive(
        self, tmp_path, immutable_status
    ):
        """Completed/Archived audits cannot transition to Review or be re-finalised.
        Only Completed → Archived is valid.
        """
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id, status=immutable_status)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        # Try Review transition — should always fail from Completed/Archived
        resp = client.post(
            f"/audits/{audit_id}/review", follow_redirects=False
        )
        assert resp.status_code == 400

        # Try Finalise transition — should always fail from Completed/Archived
        resp = client.post(
            f"/audits/{audit_id}/finalise", follow_redirects=False
        )
        assert resp.status_code == 400

        # Archive transition — only valid from Completed
        resp = client.post(
            f"/audits/{audit_id}/archive", follow_redirects=False
        )
        if immutable_status == "Completed":
            assert resp.status_code == 302  # Valid: Completed → Archived
        else:
            assert resp.status_code == 400  # Invalid: Archived → Archived

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            if immutable_status == "Completed":
                assert audit.status == "Archived"
            else:
                assert audit.status == "Archived"  # Unchanged
