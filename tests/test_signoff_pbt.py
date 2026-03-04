"""Property-based tests for audit sign-off workflow.

Feature: totika-audit-webapp
Property 21: Sign-off acknowledgement persistence

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 10.3, 10.4**
"""

import itertools
from datetime import date

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.audit import Audit, AuditScore, AuditSignOff, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SIGNOFF_STATUSES = ["Review", "Completed"]


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
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'signoff_pbt_{uid}.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_users(app):
    """Create an auditor and auditee, return (auditor_id, auditee_id, auditee_token)."""
    uid = _uid()
    with app.app_context():
        auditor = User(
            username=f"auditor_{uid}",
            email=f"auditor_{uid}@example.com",
            display_name=f"Auditor {uid}",
            password_hash=hash_password("test-pw"),
            roles="auditor",
            is_active=True,
        )
        auditee = User(
            username=f"auditee_{uid}",
            email=f"auditee_{uid}@example.com",
            display_name=f"Auditee {uid}",
            password_hash=hash_password("test-pw"),
            roles="auditee",
            is_active=True,
        )
        db.session.add_all([auditor, auditee])
        db.session.commit()
        db.session.refresh(auditor)
        db.session.refresh(auditee)
        token = create_session(auditee, ip="127.0.0.1")
        return auditor.id, auditee.id, token


def _make_template(app):
    """Create a minimal template with one criterion."""
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

        c1 = TemplateCriterion(
            section_id=section.id,
            code="MB1",
            title="Criterion 1",
            sort_order=1,
            na_allowed=False,
        )
        db.session.add(c1)
        db.session.flush()

        for score_val in range(5):
            db.session.add(
                CriterionScoringAnchor(
                    criterion_id=c1.id,
                    score=score_val,
                    description=f"Score {score_val} description",
                )
            )

        ev1 = CriterionEvidenceItem(
            criterion_id=c1.id, text="Evidence 1", sort_order=1
        )
        db.session.add(ev1)
        db.session.commit()
        return template.id


def _make_audit(app, auditor_id, auditee_id, template_id, status="Review"):
    """Create an audit assigned to the auditee with score rows."""
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=auditor_id,
            auditee_id=auditee_id,
            status=status,
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
                score = AuditScore(audit_id=audit.id, criterion_id=criterion.id)
                db.session.add(score)
                db.session.flush()
                for item in criterion.evidence_items.order_by(
                    CriterionEvidenceItem.sort_order
                ).all():
                    db.session.add(
                        EvidenceCheckState(
                            audit_score_id=score.id,
                            evidence_item_id=item.id,
                            is_checked=False,
                        )
                    )

        db.session.commit()
        return audit.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Non-empty typed names: printable strings with at least 1 non-whitespace char
st_typed_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())

# Optional comments: either empty string or some text
st_comments = st.one_of(
    st.just(""),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z", "S")),
        min_size=1,
        max_size=500,
    ),
)

# Audit status for sign-off (Review or Completed)
st_signoff_status = st.sampled_from(SIGNOFF_STATUSES)


# ---------------------------------------------------------------------------
# Property 21: Sign-off acknowledgement persistence
# ---------------------------------------------------------------------------


class TestProperty21SignOffAcknowledgementPersistence:
    """**Validates: Requirements 10.3, 10.4**

    For any typed name and comments, submitting the sign-off form should
    persist the data correctly in AuditSignOff, including the timestamp.
    """

    @given(
        typed_name=st_typed_name,
        comments=st_comments,
        status=st_signoff_status,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_signoff_persists_acknowledgement_data(
        self, tmp_path, typed_name, comments, status
    ):
        """Submitting sign-off with any valid typed name and optional comments
        should persist typed_name, comments, and a non-null timestamp."""
        app = _make_app(tmp_path)
        auditor_id, auditee_id, token = _make_users(app)
        template_id = _make_template(app)
        audit_id = _make_audit(
            app, auditor_id, auditee_id, template_id, status=status
        )

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            resp = client.post(
                f"/audits/{audit_id}/signoff",
                data={"typed_name": typed_name, "comments": comments},
                follow_redirects=False,
            )

            # Should redirect on success
            assert resp.status_code == 302, (
                f"Expected 302 redirect for typed_name={typed_name!r}, "
                f"comments={comments!r}, status={status}, got {resp.status_code}"
            )

            # Verify persistence
            with app.app_context():
                sign_off = AuditSignOff.query.filter_by(audit_id=audit_id).first()
                assert sign_off is not None, (
                    "AuditSignOff record should exist after submission"
                )
                assert sign_off.auditee_typed_name == typed_name.strip(), (
                    f"Expected typed_name={typed_name.strip()!r}, "
                    f"got {sign_off.auditee_typed_name!r}"
                )

                # Empty comments are stored as None
                expected_comments = comments.strip() or None
                assert sign_off.auditee_comments == expected_comments, (
                    f"Expected comments={expected_comments!r}, "
                    f"got {sign_off.auditee_comments!r}"
                )

                assert sign_off.auditee_acknowledged_at is not None, (
                    "auditee_acknowledged_at should be set after sign-off"
                )
