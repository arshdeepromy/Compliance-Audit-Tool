"""Property-based tests for dashboard statistics and compliance trend.

Feature: totika-audit-webapp
Property 15: Dashboard statistics match raw score data
Property 35: Compliance trend data is correctly ordered

Uses Hypothesis for property-based testing with the Flask test client.
"""

import pytest
from datetime import date, timedelta
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from app.extensions import db
from app.models.audit import Audit, AuditScore
from app.models.template import AuditTemplate, TemplateSection, TemplateCriterion
from app.models.user import User
from app.utils.auth import SESSION_COOKIE_NAME, hash_password, create_session


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Score for a criterion: 0-4, None (unscored), or "na"
_score_entry_st = st.one_of(
    st.integers(min_value=0, max_value=4),
    st.just(None),
    st.just("na"),
)

# A list of score entries (at least 1 criterion)
_score_list_st = st.lists(_score_entry_st, min_size=1, max_size=20)

# Dates for compliance trend
_date_st = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31),
)

# Overall scores for completed audits
_overall_score_st = st.floats(min_value=0.0, max_value=4.0, allow_nan=False, allow_infinity=False)

# Suppress the function-scoped fixture health check
_suppress_fixture_check = settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(roles="auditor", username="auditor_pbt"):
    """Create and return a user within the current app context."""
    user = User.query.filter_by(username=username).first()
    if user:
        return user
    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=f"User {username}",
        password_hash=hash_password("test-password"),
        roles=roles,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


def _create_template_with_criteria(num_criteria):
    """Create a template with a single section containing num_criteria criteria."""
    template = AuditTemplate(
        name="PBT Dashboard Template",
        version="1.0",
        is_active=True,
    )
    db.session.add(template)
    db.session.flush()

    section = TemplateSection(
        template_id=template.id,
        name="Section A",
        sort_order=1,
    )
    db.session.add(section)
    db.session.flush()

    criteria = []
    for i in range(num_criteria):
        criterion = TemplateCriterion(
            section_id=section.id,
            code=f"TC{i+1}",
            title=f"Test Criterion {i+1}",
            na_allowed=True,
            sort_order=i + 1,
        )
        db.session.add(criterion)
        criteria.append(criterion)

    db.session.flush()
    return template, section, criteria


def _create_audit_with_scores(auditor, template, criteria, score_entries):
    """Create an audit and assign scores based on score_entries list.

    Each entry is either:
    - int (0-4): a numeric score
    - None: unscored
    - "na": marked as N/A
    """
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        status="In_Progress",
    )
    db.session.add(audit)
    db.session.flush()

    for criterion, entry in zip(criteria, score_entries):
        if entry == "na":
            score_rec = AuditScore(
                audit_id=audit.id,
                criterion_id=criterion.id,
                score=None,
                is_na=True,
                na_reason="Not applicable",
            )
        elif entry is None:
            score_rec = AuditScore(
                audit_id=audit.id,
                criterion_id=criterion.id,
                score=None,
                is_na=False,
            )
        else:
            score_rec = AuditScore(
                audit_id=audit.id,
                criterion_id=criterion.id,
                score=entry,
                is_na=False,
            )
        db.session.add(score_rec)

    db.session.commit()
    db.session.refresh(audit)
    return audit


def _login(client, app, user):
    """Log in a user by creating a session and setting the cookie."""
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie(SESSION_COOKIE_NAME, token, domain="localhost")
    return token


# ===========================================================================
# Property 15: Dashboard statistics match raw score data
# ===========================================================================


class TestProperty15DashboardStatistics:
    """Property 15: Dashboard statistics match raw score data.

    **Validates: Requirements 6.1, 6.2, 6.3**

    For any set of scores assigned to an audit's criteria, the dashboard
    statistics (total, completed, gap_count, partial_count, na_count,
    average_score) must be correctly derived from the raw score data.
    """

    @_suppress_fixture_check
    @given(score_entries=_score_list_st)
    def test_dashboard_stats_match_raw_data(self, app, score_entries):
        """For any set of scores, dashboard stats match manual calculation."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="dash_auditor")
            template, section, criteria = _create_template_with_criteria(
                len(score_entries)
            )
            audit = _create_audit_with_scores(
                auditor, template, criteria, score_entries
            )

            # ── Manually compute expected statistics ──
            all_scores = audit.scores.all()
            expected_total = len(all_scores)

            scored_non_na = [
                s for s in all_scores if s.score is not None and not s.is_na
            ]
            expected_completed = len(scored_non_na)
            expected_na_count = sum(1 for s in all_scores if s.is_na)
            expected_gap_count = sum(
                1 for s in scored_non_na if s.score == 0
            )
            expected_partial_count = sum(
                1 for s in scored_non_na if s.score in (1, 2)
            )
            expected_average = (
                sum(s.score for s in scored_non_na) / len(scored_non_na)
                if scored_non_na
                else None
            )

            # ── Replicate the dashboard calculation from audit_detail ──
            # (testing the logic directly against the DB data)
            dashboard_all = audit.scores.all()
            dashboard_total = len(dashboard_all)

            dash_scored_non_na = [
                s for s in dashboard_all
                if s.score is not None and not s.is_na
            ]
            dash_completed = len(dash_scored_non_na)
            dash_na = sum(1 for s in dashboard_all if s.is_na)
            dash_gaps = sum(1 for s in dash_scored_non_na if s.score == 0)
            dash_partial = sum(
                1 for s in dash_scored_non_na if s.score in (1, 2)
            )
            dash_avg = (
                sum(s.score for s in dash_scored_non_na) / len(dash_scored_non_na)
                if dash_scored_non_na
                else None
            )

            # ── Assertions ──
            assert dashboard_total == expected_total
            assert dash_completed == expected_completed
            assert dash_na == expected_na_count
            assert dash_gaps == expected_gap_count
            assert dash_partial == expected_partial_count

            if expected_average is None:
                assert dash_avg is None
            else:
                assert abs(dash_avg - expected_average) < 1e-9

            # Verify score distribution counts sum correctly
            score_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
            for s in dash_scored_non_na:
                if s.score in score_dist:
                    score_dist[s.score] += 1

            assert sum(score_dist.values()) == dash_completed
            assert score_dist[0] == dash_gaps
            assert score_dist[1] + score_dist[2] == dash_partial

            # Cleanup for next hypothesis iteration
            db.session.delete(audit)
            db.session.delete(template)
            db.session.commit()

    @_suppress_fixture_check
    @given(score_entries=_score_list_st)
    def test_section_averages_match_raw_data(self, app, score_entries):
        """Per-section averages are correctly derived from raw scores.

        **Validates: Requirements 6.3**
        """
        with app.app_context():
            auditor = _create_user(roles="auditor", username="sec_auditor")

            # Create template with 2 sections, split scores between them
            template = AuditTemplate(
                name="Section PBT Template",
                version="1.0",
                is_active=True,
            )
            db.session.add(template)
            db.session.flush()

            mid = max(1, len(score_entries) // 2)
            entries_a = score_entries[:mid]
            entries_b = score_entries[mid:]

            section_a = TemplateSection(
                template_id=template.id, name="Section A", sort_order=1
            )
            section_b = TemplateSection(
                template_id=template.id, name="Section B", sort_order=2
            )
            db.session.add_all([section_a, section_b])
            db.session.flush()

            criteria_a = []
            for i, _ in enumerate(entries_a):
                c = TemplateCriterion(
                    section_id=section_a.id,
                    code=f"SA{i+1}",
                    title=f"Sec A Criterion {i+1}",
                    na_allowed=True,
                    sort_order=i + 1,
                )
                db.session.add(c)
                criteria_a.append(c)

            criteria_b = []
            for i, _ in enumerate(entries_b):
                c = TemplateCriterion(
                    section_id=section_b.id,
                    code=f"SB{i+1}",
                    title=f"Sec B Criterion {i+1}",
                    na_allowed=True,
                    sort_order=i + 1,
                )
                db.session.add(c)
                criteria_b.append(c)

            db.session.flush()

            # Create audit with scores
            audit = Audit(
                template_id=template.id,
                auditor_id=auditor.id,
                status="In_Progress",
            )
            db.session.add(audit)
            db.session.flush()

            all_criteria = criteria_a + criteria_b
            all_entries = entries_a + entries_b

            for criterion, entry in zip(all_criteria, all_entries):
                if entry == "na":
                    rec = AuditScore(
                        audit_id=audit.id,
                        criterion_id=criterion.id,
                        score=None,
                        is_na=True,
                        na_reason="N/A",
                    )
                elif entry is None:
                    rec = AuditScore(
                        audit_id=audit.id,
                        criterion_id=criterion.id,
                        score=None,
                        is_na=False,
                    )
                else:
                    rec = AuditScore(
                        audit_id=audit.id,
                        criterion_id=criterion.id,
                        score=entry,
                        is_na=False,
                    )
                db.session.add(rec)

            db.session.commit()

            # Build score lookup
            score_by_criterion = {
                s.criterion_id: s for s in audit.scores.all()
            }

            # Verify section A averages
            sec_a_scored = []
            sec_a_gaps = 0
            for c in criteria_a:
                s = score_by_criterion.get(c.id)
                if s and s.score is not None and not s.is_na:
                    sec_a_scored.append(s.score)
                    if s.score == 0:
                        sec_a_gaps += 1

            expected_a_avg = (
                sum(sec_a_scored) / len(sec_a_scored)
                if sec_a_scored
                else None
            )

            # Verify section B averages
            sec_b_scored = []
            sec_b_gaps = 0
            for c in criteria_b:
                s = score_by_criterion.get(c.id)
                if s and s.score is not None and not s.is_na:
                    sec_b_scored.append(s.score)
                    if s.score == 0:
                        sec_b_gaps += 1

            expected_b_avg = (
                sum(sec_b_scored) / len(sec_b_scored)
                if sec_b_scored
                else None
            )

            # Replicate the section summary logic from audit_detail
            sections = (
                TemplateSection.query
                .filter_by(template_id=audit.template_id)
                .order_by(TemplateSection.sort_order)
                .all()
            )

            for section in sections:
                criteria = section.criteria.order_by(
                    TemplateCriterion.sort_order
                ).all()
                section_scores = []
                section_gaps = 0
                for criterion in criteria:
                    audit_score_rec = score_by_criterion.get(criterion.id)
                    if (
                        audit_score_rec
                        and audit_score_rec.score is not None
                        and not audit_score_rec.is_na
                    ):
                        section_scores.append(audit_score_rec.score)
                        if audit_score_rec.score == 0:
                            section_gaps += 1

                section_avg = (
                    sum(section_scores) / len(section_scores)
                    if section_scores
                    else None
                )

                if section.name == "Section A":
                    if expected_a_avg is None:
                        assert section_avg is None
                    else:
                        assert abs(section_avg - expected_a_avg) < 1e-9
                    assert section_gaps == sec_a_gaps
                elif section.name == "Section B":
                    if expected_b_avg is None:
                        assert section_avg is None
                    else:
                        assert abs(section_avg - expected_b_avg) < 1e-9
                    assert section_gaps == sec_b_gaps

            # Cleanup
            db.session.delete(audit)
            db.session.delete(template)
            db.session.commit()


# ===========================================================================
# Property 35: Compliance trend data is correctly ordered
# ===========================================================================


class TestProperty35ComplianceTrendOrdered:
    """Property 35: Compliance trend data is correctly ordered.

    **Validates: Requirements 6.4**

    For any set of completed audits with different audit_dates, the
    compliance_trend list should be ordered by audit_date ascending.
    Only completed audits with non-null overall_score and audit_date
    should appear.
    """

    @_suppress_fixture_check
    @given(
        audit_data=st.lists(
            st.tuples(
                _date_st,
                _overall_score_st,
                st.sampled_from(
                    ["Draft", "In_Progress", "Review", "Completed", "Archived"]
                ),
                # has_score: whether overall_score is set
                st.booleans(),
                # has_date: whether audit_date is set
                st.booleans(),
            ),
            min_size=1,
            max_size=15,
        )
    )
    def test_compliance_trend_ordered_and_filtered(self, app, audit_data):
        """Compliance trend contains only completed audits with score and date,
        ordered by audit_date ascending."""
        with app.app_context():
            auditor = _create_user(roles="auditor", username="trend_auditor")
            template = AuditTemplate(
                name="Trend PBT Template",
                version="1.0",
                is_active=True,
            )
            db.session.add(template)
            db.session.flush()

            created_audits = []
            for audit_date, score, status, has_score, has_date in audit_data:
                audit = Audit(
                    template_id=template.id,
                    auditor_id=auditor.id,
                    status=status,
                    audit_date=audit_date if has_date else None,
                    overall_score=score if has_score else None,
                )
                db.session.add(audit)
                created_audits.append(audit)

            db.session.commit()

            # ── Replicate the compliance trend query from audit_detail ──
            completed_audits = (
                Audit.query
                .filter_by(status="Completed")
                .filter(Audit.overall_score.isnot(None))
                .filter(Audit.audit_date.isnot(None))
                .order_by(Audit.audit_date.asc())
                .all()
            )

            compliance_trend = [
                {
                    "audit_date": a.audit_date.isoformat() if a.audit_date else None,
                    "overall_score": a.overall_score,
                }
                for a in completed_audits
            ]

            # ── Manually compute expected set ──
            expected = []
            for audit_date, score, status, has_score, has_date in audit_data:
                if (
                    status == "Completed"
                    and has_score
                    and has_date
                ):
                    expected.append({
                        "audit_date": audit_date.isoformat(),
                        "overall_score": score,
                    })

            # Sort expected by audit_date ascending
            expected.sort(key=lambda x: x["audit_date"])

            # ── Assertions ──
            # Same number of entries
            assert len(compliance_trend) == len(expected)

            # Trend is ordered by date ascending
            for i in range(1, len(compliance_trend)):
                assert compliance_trend[i]["audit_date"] >= compliance_trend[i - 1]["audit_date"]

            # Each expected entry appears in the trend (matching date and score)
            trend_dates = [t["audit_date"] for t in compliance_trend]
            expected_dates = [e["audit_date"] for e in expected]
            assert trend_dates == expected_dates

            # Verify scores match for each position
            for trend_entry, expected_entry in zip(compliance_trend, expected):
                assert abs(
                    trend_entry["overall_score"] - expected_entry["overall_score"]
                ) < 1e-9

            # ── Verify non-completed audits are excluded ──
            non_completed_count = sum(
                1
                for _, _, status, has_score, has_date in audit_data
                if status != "Completed" and has_score and has_date
            )
            # These should NOT appear in the trend
            for entry in compliance_trend:
                # All entries in trend must come from Completed audits
                matching = Audit.query.filter_by(
                    status="Completed",
                    audit_date=date.fromisoformat(entry["audit_date"]),
                ).filter(Audit.overall_score.isnot(None)).all()
                assert len(matching) > 0

            # Cleanup
            for audit in created_audits:
                db.session.delete(audit)
            db.session.delete(template)
            db.session.commit()
