"""Property-based tests for Criteria Scoring.

Feature: totika-audit-webapp
Property 13: Scoring data round-trip persistence
Property 14: N/A exclusion from score calculation

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.7**
"""

import itertools

import pytest
from hypothesis import given, settings, HealthCheck, assume
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
# Helpers
# ---------------------------------------------------------------------------

_counter = itertools.count()


def _uid():
    return next(_counter)


def _make_app(tmp_path):
    """Create a fresh Flask app with its own SQLite DB."""
    uid = _uid()

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'scoring_pbt_{uid}.db'}"

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


def _make_template_with_criteria(app, num_criteria, na_allowed_flags, evidence_counts):
    """Create a template with one section and the specified number of criteria.

    Args:
        num_criteria: How many criteria to create.
        na_allowed_flags: List of booleans, one per criterion.
        evidence_counts: List of ints, number of evidence items per criterion.

    Returns:
        (template_id, list of criterion codes, dict mapping code -> list of evidence_item_ids)
    """
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
        evidence_map = {}
        for i in range(num_criteria):
            code = f"C{i + 1}"
            criterion = TemplateCriterion(
                section_id=section.id,
                code=code,
                title=f"Criterion {i + 1}",
                sort_order=i + 1,
                na_allowed=na_allowed_flags[i],
            )
            db.session.add(criterion)
            db.session.flush()

            item_ids = []
            for j in range(evidence_counts[i]):
                item = CriterionEvidenceItem(
                    criterion_id=criterion.id,
                    text=f"Evidence {j + 1}",
                    sort_order=j + 1,
                )
                db.session.add(item)
                db.session.flush()
                item_ids.append(item.id)

            codes.append(code)
            evidence_map[code] = item_ids

        db.session.commit()
        return template.id, codes, evidence_map


def _make_audit(app, user_id, template_id, status="Draft"):
    """Create an audit with AuditScore and EvidenceCheckState rows."""
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=user_id,
            status=status,
        )
        db.session.add(audit)
        db.session.flush()

        sections = TemplateSection.query.filter_by(template_id=template_id).all()
        for section in sections:
            criteria = TemplateCriterion.query.filter_by(section_id=section.id).all()
            for criterion in criteria:
                score = AuditScore(audit_id=audit.id, criterion_id=criterion.id)
                db.session.add(score)
                db.session.flush()

                evidence_items = CriterionEvidenceItem.query.filter_by(
                    criterion_id=criterion.id
                ).all()
                for item in evidence_items:
                    check_state = EvidenceCheckState(
                        audit_score_id=score.id,
                        evidence_item_id=item.id,
                        is_checked=False,
                    )
                    db.session.add(check_state)

        db.session.commit()
        return audit.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Score values 0-4
st_score = st.integers(min_value=0, max_value=4)

# Notes text — printable strings, limited size for speed
st_notes = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=0,
    max_size=100,
)


# ---------------------------------------------------------------------------
# Property 13: Scoring data round-trip persistence
# ---------------------------------------------------------------------------


class TestProperty13ScoringRoundTrip:
    """**Validates: Requirements 5.2, 5.4, 5.5**

    For any valid score (0–4), notes, and evidence check states, saving
    via the API and then reading back should return identical data.
    """

    @given(
        score_value=st_score,
        notes=st_notes,
        ev_check_1=st.booleans(),
        ev_check_2=st.booleans(),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_score_notes_evidence_round_trip(
        self, tmp_path, score_value, notes, ev_check_1, ev_check_2
    ):
        """Saving a score, notes, and evidence checks via the API then
        querying the DB should return identical values.
        """
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes, evidence_map = _make_template_with_criteria(
            app,
            num_criteria=1,
            na_allowed_flags=[False],
            evidence_counts=[2],
        )
        audit_id = _make_audit(app, user_id, template_id)

        code = codes[0]
        ev_ids = evidence_map[code]

        # Build evidence_checks payload
        evidence_checks = {
            str(ev_ids[0]): ev_check_1,
            str(ev_ids[1]): ev_check_2,
        }

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.put(
            f"/api/audits/{audit_id}/score",
            json={
                "criterion_code": code,
                "score": score_value,
                "is_na": False,
                "na_reason": "",
                "notes": notes,
                "evidence_checks": evidence_checks,
            },
        )

        assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data["ok"] is True
        assert data["score"] == score_value

        # Verify round-trip by reading from DB
        with app.app_context():
            audit_score = AuditScore.query.filter_by(audit_id=audit_id).first()
            assert audit_score.score == score_value
            assert audit_score.is_na is False
            # Notes: empty string is stored as None
            expected_notes = notes if notes else None
            assert audit_score.notes == expected_notes

            # Verify evidence check states
            for ev_id, expected_checked in [(ev_ids[0], ev_check_1), (ev_ids[1], ev_check_2)]:
                check = EvidenceCheckState.query.filter_by(
                    audit_score_id=audit_score.id,
                    evidence_item_id=ev_id,
                ).first()
                assert check is not None, f"EvidenceCheckState not found for item {ev_id}"
                assert check.is_checked == expected_checked, (
                    f"Evidence item {ev_id}: expected is_checked={expected_checked}, "
                    f"got {check.is_checked}"
                )

    @given(
        score_value=st_score,
        notes=st_notes,
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_na_round_trip_when_allowed(self, tmp_path, score_value, notes):
        """When a criterion allows N/A, marking it N/A with a reason should
        persist correctly and the score should be cleared.
        """
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes, evidence_map = _make_template_with_criteria(
            app,
            num_criteria=1,
            na_allowed_flags=[True],
            evidence_counts=[0],
        )
        audit_id = _make_audit(app, user_id, template_id)

        code = codes[0]
        na_reason = "Not applicable for this site"

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.put(
            f"/api/audits/{audit_id}/score",
            json={
                "criterion_code": code,
                "score": score_value,
                "is_na": True,
                "na_reason": na_reason,
                "notes": notes,
                "evidence_checks": {},
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["is_na"] is True

        # Verify in DB: score should be None when N/A
        with app.app_context():
            audit_score = AuditScore.query.filter_by(audit_id=audit_id).first()
            assert audit_score.is_na is True
            assert audit_score.score is None
            assert audit_score.na_reason == na_reason


# ---------------------------------------------------------------------------
# Property 14: N/A exclusion from score calculation
# ---------------------------------------------------------------------------


class TestProperty14NAExclusionFromScoreCalculation:
    """**Validates: Requirements 5.3, 5.7**

    When criteria are marked N/A, they must be excluded from the overall
    average score calculation. The overall score should equal
    sum(non-NA scores) / count(non-NA scored criteria).
    """

    @given(
        data=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=4),
                st.booleans(),  # is_na
            ),
            min_size=2,
            max_size=6,
        ),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_overall_score_excludes_na_criteria(self, tmp_path, data):
        """For a set of criteria with mixed scores and N/A flags, the
        overall_score should equal sum(non-NA scores) / count(non-NA scored).
        """
        num_criteria = len(data)

        # All criteria allow N/A so we can freely mark them
        na_allowed_flags = [True] * num_criteria
        evidence_counts = [0] * num_criteria

        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes, evidence_map = _make_template_with_criteria(
            app, num_criteria, na_allowed_flags, evidence_counts
        )
        audit_id = _make_audit(app, user_id, template_id)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        # Save each criterion's score
        for i, (score_val, is_na) in enumerate(data):
            payload = {
                "criterion_code": codes[i],
                "score": score_val,
                "is_na": is_na,
                "na_reason": "Not applicable" if is_na else "",
                "notes": "",
                "evidence_checks": {},
            }
            resp = client.put(f"/api/audits/{audit_id}/score", json=payload)
            assert resp.status_code == 200, (
                f"Failed to save score for {codes[i]}: {resp.get_json()}"
            )

        # Calculate expected overall score
        non_na_scores = [s for s, na in data if not na]
        if non_na_scores:
            expected_overall = sum(non_na_scores) / len(non_na_scores)
        else:
            expected_overall = None

        # Read the audit's overall_score from DB
        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            if expected_overall is None:
                assert audit.overall_score is None, (
                    f"Expected None overall_score when all criteria are N/A, "
                    f"got {audit.overall_score}"
                )
            else:
                assert audit.overall_score is not None, (
                    "Expected a numeric overall_score but got None"
                )
                assert abs(audit.overall_score - expected_overall) < 1e-9, (
                    f"Expected overall_score={expected_overall}, "
                    f"got {audit.overall_score}"
                )

    @given(
        scores=st.lists(
            st.integers(min_value=0, max_value=4),
            min_size=2,
            max_size=6,
        ),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_no_na_means_all_scores_included(self, tmp_path, scores):
        """When no criteria are N/A, the overall score should be the
        simple average of all scores.
        """
        num_criteria = len(scores)
        na_allowed_flags = [False] * num_criteria
        evidence_counts = [0] * num_criteria

        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes, evidence_map = _make_template_with_criteria(
            app, num_criteria, na_allowed_flags, evidence_counts
        )
        audit_id = _make_audit(app, user_id, template_id)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        for i, score_val in enumerate(scores):
            resp = client.put(
                f"/api/audits/{audit_id}/score",
                json={
                    "criterion_code": codes[i],
                    "score": score_val,
                    "is_na": False,
                    "na_reason": "",
                    "notes": "",
                    "evidence_checks": {},
                },
            )
            assert resp.status_code == 200

        expected_overall = sum(scores) / len(scores)

        with app.app_context():
            audit = db.session.get(Audit, audit_id)
            assert audit.overall_score is not None
            assert abs(audit.overall_score - expected_overall) < 1e-9, (
                f"Expected overall_score={expected_overall}, got {audit.overall_score}"
            )

    @given(
        score_value=st_score,
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_na_rejected_when_not_allowed(self, tmp_path, score_value):
        """Marking a criterion as N/A when na_allowed is False should be rejected."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id, codes, evidence_map = _make_template_with_criteria(
            app,
            num_criteria=1,
            na_allowed_flags=[False],
            evidence_counts=[0],
        )
        audit_id = _make_audit(app, user_id, template_id)

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")

        resp = client.put(
            f"/api/audits/{audit_id}/score",
            json={
                "criterion_code": codes[0],
                "score": score_value,
                "is_na": True,
                "na_reason": "Some reason",
                "notes": "",
                "evidence_checks": {},
            },
        )

        assert resp.status_code == 400, (
            f"Expected 400 when N/A not allowed, got {resp.status_code}"
        )
        data = resp.get_json()
        assert "error" in data
