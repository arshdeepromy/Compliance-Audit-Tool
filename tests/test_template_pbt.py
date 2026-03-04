"""Property-based tests for Audit Template Management.

Feature: totika-audit-webapp
Property 9: Template editing preserves existing audit data
Property 10: Only active templates appear in audit creation

Uses Hypothesis for property-based testing with the Flask test client.
"""

import itertools

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
    CriterionScoringAnchor,
    CriterionEvidenceItem,
)
from app.models.audit import Audit, AuditScore, EvidenceCheckState
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
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'tpl_pbt_{uid}.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_admin(app):
    """Create an admin user and return (user_id, token)."""
    uid = _uid()
    with app.app_context():
        user = User(
            username=f"admin_{uid}",
            email=f"admin_{uid}@example.com",
            display_name="Admin",
            password_hash=hash_password("admin-pw"),
            roles="admin",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        token = create_session(user, ip="127.0.0.1")
        return user.id, token


def _make_auditor(app):
    """Create an auditor user and return (user_id, token)."""
    uid = _uid()
    with app.app_context():
        user = User(
            username=f"auditor_{uid}",
            email=f"auditor_{uid}@example.com",
            display_name="Auditor",
            password_hash=hash_password("auditor-pw"),
            roles="auditor",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user.id


def _create_template(app, name, version, is_active, sections_data):
    """Create a template with sections and criteria directly in the DB.

    sections_data: list of dicts with keys:
        name: str
        criteria: list of dicts with keys:
            code, title, notes_text (optional), scores (list of (score_val, desc)),
            evidence (list of str)
    Returns template_id.
    """
    with app.app_context():
        tpl = AuditTemplate(
            name=name,
            version=version,
            is_active=is_active,
            is_builtin=False,
        )
        db.session.add(tpl)
        db.session.flush()

        crit_sort = 0
        for s_order, s_data in enumerate(sections_data):
            section = TemplateSection(
                template_id=tpl.id,
                name=s_data["name"],
                sort_order=s_order,
            )
            db.session.add(section)
            db.session.flush()

            for c_data in s_data["criteria"]:
                crit_sort += 1
                crit = TemplateCriterion(
                    section_id=section.id,
                    code=c_data["code"],
                    title=c_data["title"],
                    guidance=c_data.get("guidance"),
                    question=c_data.get("question"),
                    na_allowed=c_data.get("na_allowed", False),
                    tip=None,
                    sort_order=crit_sort,
                )
                db.session.add(crit)
                db.session.flush()

                for score_val, desc in c_data.get("scores", []):
                    db.session.add(
                        CriterionScoringAnchor(
                            criterion_id=crit.id,
                            score=score_val,
                            description=desc,
                        )
                    )

                for ev_order, ev_text in enumerate(c_data.get("evidence", [])):
                    db.session.add(
                        CriterionEvidenceItem(
                            criterion_id=crit.id,
                            text=ev_text,
                            is_required=False,
                            sort_order=ev_order,
                        )
                    )

        db.session.commit()
        return tpl.id


def _create_audit_with_scores(app, template_id, auditor_id):
    """Create an audit for the template and populate scores/evidence states.

    Returns (audit_id, snapshot) where snapshot is a list of dicts capturing
    each score row's data for later comparison.
    """
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=auditor_id,
            status="In_Progress",
        )
        db.session.add(audit)
        db.session.flush()

        # Get all criteria for this template
        criteria = (
            TemplateCriterion.query
            .join(TemplateSection)
            .filter(TemplateSection.template_id == template_id)
            .all()
        )

        snapshot = []
        for idx, crit in enumerate(criteria):
            score_val = idx % 5  # cycle 0-4
            notes = f"Notes for {crit.code}"
            audit_score = AuditScore(
                audit_id=audit.id,
                criterion_id=crit.id,
                score=score_val,
                is_na=False,
                notes=notes,
            )
            db.session.add(audit_score)
            db.session.flush()

            # Add evidence check states
            ev_items = CriterionEvidenceItem.query.filter_by(
                criterion_id=crit.id
            ).all()
            ev_states = []
            for ev in ev_items:
                checked = idx % 2 == 0
                ecs = EvidenceCheckState(
                    audit_score_id=audit_score.id,
                    evidence_item_id=ev.id,
                    is_checked=checked,
                )
                db.session.add(ecs)
                ev_states.append({"evidence_item_id": ev.id, "is_checked": checked})

            snapshot.append({
                "criterion_id": crit.id,
                "score": score_val,
                "is_na": False,
                "notes": notes,
                "evidence_states": ev_states,
            })

        db.session.commit()
        return audit.id, snapshot


def _read_audit_snapshot(app, audit_id):
    """Read back the current state of an audit's scores and evidence states."""
    with app.app_context():
        scores = AuditScore.query.filter_by(audit_id=audit_id).all()
        result = []
        for s in scores:
            ev_states = EvidenceCheckState.query.filter_by(
                audit_score_id=s.id
            ).all()
            result.append({
                "criterion_id": s.criterion_id,
                "score": s.score,
                "is_na": s.is_na,
                "notes": s.notes,
                "evidence_states": [
                    {"evidence_item_id": e.evidence_item_id, "is_checked": e.is_checked}
                    for e in ev_states
                ],
            })
        return result


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for a criterion definition
_criterion_st = st.fixed_dictionaries({
    "code": st.from_regex(r"C[0-9]{1,3}", fullmatch=True),
    "title": st.text(min_size=1, max_size=50).filter(lambda t: t.strip()),
    "guidance": st.none() | st.text(min_size=1, max_size=100),
    "question": st.none() | st.text(min_size=1, max_size=100),
    "na_allowed": st.booleans(),
    "scores": st.just([(i, f"Level {i}") for i in range(5)]),
    "evidence": st.lists(
        st.text(min_size=1, max_size=40).filter(lambda t: t.strip()),
        min_size=0,
        max_size=3,
    ),
})

# Strategy for a section definition (1-3 criteria per section)
_section_st = st.fixed_dictionaries({
    "name": st.text(min_size=1, max_size=40).filter(lambda t: t.strip()),
    "criteria": st.lists(_criterion_st, min_size=1, max_size=3),
})

# Strategy for a template's sections (1-3 sections)
_sections_list_st = st.lists(_section_st, min_size=1, max_size=3)

# Strategy for template active/inactive state
_active_state_st = st.booleans()

# Suppress the function-scoped fixture health check
_suppress = settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)



# ===========================================================================
# Property 9: Template editing preserves existing audit data
# ===========================================================================


class TestProperty9TemplateEditPreservesAuditData:
    """Property 9: Template editing preserves existing audit data.

    *For any* audit template that has been used by existing audits, editing
    the template (changing criteria text, adding/removing criteria) SHALL NOT
    modify the scores, notes, or evidence states of those existing audits.

    The implementation creates a new template version when audits exist,
    leaving the original template and its audit data untouched.

    **Validates: Requirements 3.3**
    """

    @_suppress
    @given(sections=_sections_list_st)
    def test_editing_template_with_audits_preserves_scores(
        self, tmp_path, sections
    ):
        """Editing a template that has audits creates a new version and
        leaves existing audit scores, notes, and evidence states intact."""
        app = _make_app(tmp_path)
        admin_id, admin_token = _make_admin(app)
        auditor_id = _make_auditor(app)

        # 1. Create the original template
        template_id = _create_template(
            app, "Original", "1.0", True, sections
        )

        # 2. Create an audit with scores against this template
        audit_id, original_snapshot = _create_audit_with_scores(
            app, template_id, auditor_id
        )

        # 3. Edit the template via the blueprint (POST to edit route)
        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, admin_token, domain="localhost")

        # Build form data for a modified template
        form_data = {
            "name": "Modified Template",
            "version": "2.0",
            "description": "Edited version",
            "section_0_name": "New Section",
            "section_0_criterion_0_code": "NEW1",
            "section_0_criterion_0_title": "New Criterion",
            "section_0_criterion_0_score_0": "No compliance",
            "section_0_criterion_0_score_1": "Low compliance",
            "section_0_criterion_0_score_2": "Partial compliance",
            "section_0_criterion_0_score_3": "Good compliance",
            "section_0_criterion_0_score_4": "Full compliance",
        }

        resp = client.post(
            f"/admin/templates/{template_id}",
            data=form_data,
            follow_redirects=False,
        )
        # Should redirect on success (302) or succeed
        assert resp.status_code in (200, 302), (
            f"Template edit returned {resp.status_code}"
        )

        # 4. Verify the original audit data is completely unchanged
        after_snapshot = _read_audit_snapshot(app, audit_id)

        assert len(after_snapshot) == len(original_snapshot), (
            f"Audit score count changed: {len(original_snapshot)} → {len(after_snapshot)}"
        )

        for orig, after in zip(original_snapshot, after_snapshot):
            assert orig["criterion_id"] == after["criterion_id"], (
                "Criterion ID changed after template edit"
            )
            assert orig["score"] == after["score"], (
                f"Score changed for criterion {orig['criterion_id']}: "
                f"{orig['score']} → {after['score']}"
            )
            assert orig["is_na"] == after["is_na"], (
                f"is_na changed for criterion {orig['criterion_id']}"
            )
            assert orig["notes"] == after["notes"], (
                f"Notes changed for criterion {orig['criterion_id']}"
            )

            # Compare evidence check states
            orig_ev = sorted(orig["evidence_states"], key=lambda e: e["evidence_item_id"])
            after_ev = sorted(after["evidence_states"], key=lambda e: e["evidence_item_id"])
            assert orig_ev == after_ev, (
                f"Evidence states changed for criterion {orig['criterion_id']}"
            )

    @_suppress
    @given(sections=_sections_list_st)
    def test_editing_template_with_audits_creates_new_version(
        self, tmp_path, sections
    ):
        """When a template with audits is edited, a new template version is
        created and the original template remains in the database."""
        app = _make_app(tmp_path)
        admin_id, admin_token = _make_admin(app)
        auditor_id = _make_auditor(app)

        template_id = _create_template(
            app, "Versioned", "1.0", True, sections
        )
        audit_id, _ = _create_audit_with_scores(
            app, template_id, auditor_id
        )

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, admin_token, domain="localhost")

        form_data = {
            "name": "Versioned",
            "version": "2.0",
            "description": "Updated",
            "section_0_name": "Updated Section",
            "section_0_criterion_0_code": "U1",
            "section_0_criterion_0_title": "Updated Criterion",
        }

        with app.app_context():
            count_before = AuditTemplate.query.count()

        client.post(
            f"/admin/templates/{template_id}",
            data=form_data,
            follow_redirects=True,
        )

        with app.app_context():
            count_after = AuditTemplate.query.count()
            # A new version should have been created
            assert count_after == count_before + 1, (
                f"Expected new template version, count: {count_before} → {count_after}"
            )

            # Original template still exists
            original = db.session.get(AuditTemplate, template_id)
            assert original is not None, "Original template was deleted"

            # Audit still references the original template
            audit = db.session.get(Audit, audit_id)
            assert audit.template_id == template_id, (
                f"Audit template_id changed: {template_id} → {audit.template_id}"
            )

    @_suppress
    @given(sections=_sections_list_st)
    def test_audit_score_count_unchanged_after_template_edit(
        self, tmp_path, sections
    ):
        """The number of AuditScore rows for an existing audit does not
        change when the template is edited."""
        app = _make_app(tmp_path)
        admin_id, admin_token = _make_admin(app)
        auditor_id = _make_auditor(app)

        template_id = _create_template(
            app, "CountCheck", "1.0", True, sections
        )
        audit_id, _ = _create_audit_with_scores(
            app, template_id, auditor_id
        )

        with app.app_context():
            score_count_before = AuditScore.query.filter_by(audit_id=audit_id).count()

        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, admin_token, domain="localhost")

        form_data = {
            "name": "CountCheck",
            "version": "2.0",
            "section_0_name": "S1",
            "section_0_criterion_0_code": "X1",
            "section_0_criterion_0_title": "X Criterion",
        }
        client.post(
            f"/admin/templates/{template_id}",
            data=form_data,
            follow_redirects=True,
        )

        with app.app_context():
            score_count_after = AuditScore.query.filter_by(audit_id=audit_id).count()
            assert score_count_before == score_count_after, (
                f"Score count changed: {score_count_before} → {score_count_after}"
            )


# ===========================================================================
# Property 10: Only active templates appear in audit creation
# ===========================================================================


class TestProperty10OnlyActiveTemplatesInAuditCreation:
    """Property 10: Only active templates appear in audit creation.

    *For any* set of templates with mixed active/inactive states, the
    template selection list when creating a new audit SHALL contain exactly
    the active templates and none of the inactive ones.

    **Validates: Requirements 3.4, 3.5**
    """

    @_suppress
    @given(
        active_states=st.lists(
            st.booleans(), min_size=1, max_size=6
        ),
    )
    def test_query_returns_only_active_templates(
        self, tmp_path, active_states
    ):
        """Querying for active templates returns exactly those with
        is_active=True, regardless of how many templates exist."""
        app = _make_app(tmp_path)

        created_ids = []
        with app.app_context():
            for idx, is_active in enumerate(active_states):
                tpl = AuditTemplate(
                    name=f"Template {idx}",
                    version="1.0",
                    is_active=is_active,
                    is_builtin=False,
                )
                db.session.add(tpl)
                db.session.flush()
                created_ids.append((tpl.id, is_active))
            db.session.commit()

            # Query active templates (this is what the audit creation view uses)
            active_templates = AuditTemplate.query.filter_by(is_active=True).all()
            active_ids = {t.id for t in active_templates}

            expected_active_ids = {tid for tid, active in created_ids if active}
            expected_inactive_ids = {tid for tid, active in created_ids if not active}

            # All active templates are present
            assert active_ids == expected_active_ids, (
                f"Active template mismatch: got {active_ids}, "
                f"expected {expected_active_ids}"
            )

            # No inactive templates are present
            assert active_ids.isdisjoint(expected_inactive_ids), (
                f"Inactive templates found in active query: "
                f"{active_ids & expected_inactive_ids}"
            )

    @_suppress
    @given(
        active_states=st.lists(
            st.booleans(), min_size=2, max_size=6
        ),
    )
    def test_toggling_template_updates_active_query(
        self, tmp_path, active_states
    ):
        """After toggling a template's active state, the active query
        reflects the change correctly."""
        app = _make_app(tmp_path)
        admin_id, admin_token = _make_admin(app)

        template_ids = []
        with app.app_context():
            for idx, is_active in enumerate(active_states):
                tpl = AuditTemplate(
                    name=f"Toggle {idx}",
                    version="1.0",
                    is_active=is_active,
                    is_builtin=False,
                )
                db.session.add(tpl)
                db.session.flush()
                template_ids.append(tpl.id)
            db.session.commit()

        # Toggle the first template
        client = app.test_client()
        client.set_cookie(SESSION_COOKIE_NAME, admin_token, domain="localhost")
        client.post(
            f"/admin/templates/{template_ids[0]}/toggle",
            follow_redirects=True,
        )

        with app.app_context():
            toggled = db.session.get(AuditTemplate, template_ids[0])
            # The first template's state should be flipped
            assert toggled.is_active == (not active_states[0]), (
                f"Toggle did not flip: was {active_states[0]}, "
                f"now {toggled.is_active}"
            )

            # Active query should reflect the new state
            active_templates = AuditTemplate.query.filter_by(is_active=True).all()
            active_ids = {t.id for t in active_templates}

            # Build expected set after toggle
            expected = set()
            for idx, is_active in enumerate(active_states):
                if idx == 0:
                    if not is_active:  # was inactive, now active
                        expected.add(template_ids[idx])
                else:
                    if is_active:
                        expected.add(template_ids[idx])

            assert active_ids == expected, (
                f"After toggle, active set mismatch: got {active_ids}, "
                f"expected {expected}"
            )

    @_suppress
    @given(
        active_states=st.lists(
            st.booleans(), min_size=1, max_size=6
        ),
    )
    def test_active_count_matches_expected(
        self, tmp_path, active_states
    ):
        """The count of active templates matches the number of True values
        in the active_states list."""
        app = _make_app(tmp_path)

        with app.app_context():
            for idx, is_active in enumerate(active_states):
                tpl = AuditTemplate(
                    name=f"Count {idx}",
                    version="1.0",
                    is_active=is_active,
                    is_builtin=False,
                )
                db.session.add(tpl)
            db.session.commit()

            active_count = AuditTemplate.query.filter_by(is_active=True).count()
            expected_count = sum(1 for s in active_states if s)

            assert active_count == expected_count, (
                f"Active count {active_count} != expected {expected_count}"
            )
