"""Property-based tests for file uploads and attachment deletion.

Feature: totika-audit-webapp
Property 18: File upload validation
Property 19: Attachment deletion respects audit status

Uses Hypothesis for property-based testing with the Flask test client.

**Validates: Requirements 8.1, 8.2, 8.4, 8.5**
"""

import io
import itertools
import os
from datetime import date

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.attachment import EvidenceAttachment
from app.models.audit import Audit, AuditScore, EvidenceCheckState
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

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Statuses where deletion should succeed
MUTABLE_STATUSES = ["Draft", "In_Progress", "Review"]
# Statuses where deletion should be rejected
IMMUTABLE_STATUSES = ["Completed", "Archived"]
ALL_STATUSES = MUTABLE_STATUSES + IMMUTABLE_STATUSES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = itertools.count()


def _uid():
    return next(_counter)


def _make_app(tmp_path):
    """Create a fresh Flask app with its own SQLite DB and upload dir."""
    uid = _uid()
    upload_dir = tmp_path / f"uploads_{uid}"
    upload_dir.mkdir()

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'uploads_pbt_{uid}.db'}"
        UPLOAD_FOLDER = str(upload_dir)
        MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _make_user(app, roles="auditor,admin"):
    """Create a user and return (user_id, token)."""
    uid = _uid()
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
    """Create a minimal template with one criterion (MB1)."""
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


def _make_audit(app, user_id, template_id, status="Draft"):
    """Create an audit with score rows for all criteria."""
    with app.app_context():
        audit = Audit(
            template_id=template_id,
            auditor_id=user_id,
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


def _upload_file(client, audit_id, filename, content):
    """Upload a file and return the response."""
    data = {"file": (io.BytesIO(content), filename)}
    return client.post(
        f"/audits/{audit_id}/score/MB1/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for allowed file extensions
st_allowed_ext = st.sampled_from(sorted(ALLOWED_EXTENSIONS))

# Strategy for disallowed file extensions — common types that should be rejected
st_disallowed_ext = st.sampled_from([
    "exe", "bat", "sh", "py", "js", "html", "css", "txt", "csv",
    "zip", "tar", "gz", "rar", "mp3", "mp4", "avi", "mov", "bmp",
    "gif", "svg", "xml", "json", "yaml", "sql", "dll", "so",
])

# Strategy for file extension (either allowed or disallowed)
st_any_ext = st.one_of(st_allowed_ext, st_disallowed_ext)

# Strategy for a simple filename base (alphanumeric, 1-20 chars)
st_filename_base = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=20,
)

# Strategy for file content that is within size limit
st_small_content = st.binary(min_size=1, max_size=1024)

# Strategy for audit statuses
st_mutable_status = st.sampled_from(MUTABLE_STATUSES)
st_immutable_status = st.sampled_from(IMMUTABLE_STATUSES)
st_any_status = st.sampled_from(ALL_STATUSES)


# ---------------------------------------------------------------------------
# Property 18: File upload validation
# ---------------------------------------------------------------------------


class TestProperty18FileUploadValidation:
    """**Validates: Requirements 8.1, 8.2, 8.5**

    For any file upload:
    - Files with allowed extensions (pdf, png, jpg, jpeg, docx) and size <= 20 MB
      should be accepted (302 redirect) and persisted.
    - Files with disallowed extensions should be rejected with an error flash.
    - Files exceeding 20 MB should be rejected.
    """

    @given(ext=st_allowed_ext, content=st_small_content)
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_allowed_extensions_accepted(self, tmp_path, ext, content):
        """Uploading a file with an allowed extension should succeed (302)."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            filename = f"testfile.{ext}"
            resp = _upload_file(client, audit_id, filename, content)

            # Should redirect back to scoring form (success)
            assert resp.status_code == 302, (
                f"Expected 302 for allowed extension '.{ext}', got {resp.status_code}"
            )

            # Verify attachment record was created
            with app.app_context():
                att = EvidenceAttachment.query.first()
                assert att is not None, f"No attachment record for '.{ext}'"
                assert att.original_filename == filename
                assert att.file_size == len(content)

                # Verify file exists on disk
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], att.filename)
                assert os.path.exists(filepath)

    @given(ext=st_disallowed_ext, content=st_small_content)
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_disallowed_extensions_rejected(self, tmp_path, ext, content):
        """Uploading a file with a disallowed extension should be rejected."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            filename = f"testfile.{ext}"
            resp = _upload_file(client, audit_id, filename, content)

            # Should redirect (302) but with error flash, or follow redirects to check
            # The upload route redirects back on error too, so follow to check flash
            resp_followed = client.post(
                f"/audits/{audit_id}/score/MB1/upload",
                data={"file": (io.BytesIO(content), filename)},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert b"File type not allowed" in resp_followed.data, (
                f"Expected rejection for '.{ext}' but no error flash found"
            )

            # Verify no attachment was created
            with app.app_context():
                assert EvidenceAttachment.query.count() == 0, (
                    f"Attachment should not be created for '.{ext}'"
                )

    @given(ext=st_allowed_ext)
    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_oversized_file_rejected(self, tmp_path, ext):
        """Uploading a file > 20 MB should be rejected regardless of type."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        audit_id = _make_audit(app, user_id, template_id)

        # Content just over 20 MB
        oversized_content = b"x" * (MAX_FILE_SIZE + 1)

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            filename = f"bigfile.{ext}"
            resp = _upload_file(client, audit_id, filename, oversized_content)

            # Either Flask's MAX_CONTENT_LENGTH returns 413 or our validation
            # catches it with a redirect. Either way, no attachment should exist.
            with app.app_context():
                assert EvidenceAttachment.query.count() == 0, (
                    f"Oversized file with '.{ext}' should not be stored"
                )


# ---------------------------------------------------------------------------
# Property 19: Attachment deletion respects audit status
# ---------------------------------------------------------------------------


class TestProperty19AttachmentDeletionRespectsStatus:
    """**Validates: Requirements 8.4**

    For any attachment:
    - Deletion should succeed on Draft, In_Progress, or Review audits.
    - Deletion should be rejected on Completed or Archived audits.
    """

    @given(status=st_mutable_status)
    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_deletion_succeeds_on_mutable_audits(self, tmp_path, status):
        """Deleting an attachment on a Draft/In_Progress/Review audit should succeed."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        # Create as Draft so upload works, then change status
        audit_id = _make_audit(app, user_id, template_id, status="Draft")

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            # Upload a file
            content = b"test file content"
            resp = _upload_file(client, audit_id, "evidence.pdf", content)
            assert resp.status_code == 302

            with app.app_context():
                att = EvidenceAttachment.query.first()
                assert att is not None
                att_id = att.id
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], att.filename)
                assert os.path.exists(filepath)

                # Change audit status to the target
                audit = db.session.get(Audit, audit_id)
                audit.status = status
                db.session.commit()

            # Attempt deletion
            resp = client.delete(f"/api/attachments/{att_id}")
            assert resp.status_code == 200, (
                f"Expected 200 for deletion on '{status}' audit, got {resp.status_code}"
            )
            data = resp.get_json()
            assert data["ok"] is True

            # Verify record and file removed
            with app.app_context():
                assert EvidenceAttachment.query.get(att_id) is None, (
                    f"Attachment record should be removed on '{status}' audit"
                )
                assert not os.path.exists(filepath), (
                    f"File should be removed from disk on '{status}' audit"
                )

    @given(status=st_immutable_status)
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_deletion_rejected_on_immutable_audits(self, tmp_path, status):
        """Deleting an attachment on a Completed/Archived audit should be rejected."""
        app = _make_app(tmp_path)
        user_id, token = _make_user(app)
        template_id = _make_template(app)
        # Create as Draft so upload works
        audit_id = _make_audit(app, user_id, template_id, status="Draft")

        with app.test_client() as client:
            client.set_cookie("session_token", token, domain="localhost")

            # Upload a file
            content = b"test file content"
            resp = _upload_file(client, audit_id, "evidence.pdf", content)
            assert resp.status_code == 302

            with app.app_context():
                att = EvidenceAttachment.query.first()
                assert att is not None
                att_id = att.id
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], att.filename)

                # Change audit status to immutable
                audit = db.session.get(Audit, audit_id)
                audit.status = status
                db.session.commit()

            # Attempt deletion — should be rejected
            resp = client.delete(f"/api/attachments/{att_id}")
            assert resp.status_code == 400, (
                f"Expected 400 for deletion on '{status}' audit, got {resp.status_code}"
            )
            data = resp.get_json()
            assert "locked" in data["error"].lower(), (
                f"Error message should mention 'locked' for '{status}' audit"
            )

            # Verify record and file still exist
            with app.app_context():
                assert EvidenceAttachment.query.get(att_id) is not None, (
                    f"Attachment record should still exist on '{status}' audit"
                )
                assert os.path.exists(filepath), (
                    f"File should still exist on disk for '{status}' audit"
                )
