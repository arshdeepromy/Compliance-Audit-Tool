"""Unit tests for file upload and attachment management (task 10.1).

Covers:
- Successful file upload (Req 8.1)
- File type validation — reject invalid types (Req 8.2, 8.5)
- File size validation — reject > 20 MB (Req 8.2, 8.5)
- Attachment deletion (Req 8.4)
- Rejection on Completed/Archived audits (Req 4.6, 8.4)
- Download route (Req 8.3)
"""

import io
import os
import pytest
from datetime import date

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.attachment import EvidenceAttachment
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.template import (
    AuditTemplate,
    TemplateCriterion,
    TemplateSection,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
)
from app.models.user import User
from app.utils.auth import hash_password, create_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with a file-based SQLite DB and temp upload dir."""
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    class Cfg(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        UPLOAD_FOLDER = str(upload_dir)
        MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    application = create_app(config_class=Cfg, run_startup=False)
    return application


@pytest.fixture(autouse=True)
def setup_db(app):
    with app.app_context():
        _db.create_all()
        yield
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(roles="auditor", username="auditor1"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        display_name=username.title(),
        password_hash=hash_password("password123"),
        roles=roles,
        is_active=True,
    )
    _db.session.add(user)
    _db.session.commit()
    _db.session.refresh(user)
    return user


def _create_template():
    template = AuditTemplate(name="Test Template", version="1.0", is_active=True)
    _db.session.add(template)
    _db.session.flush()

    section = TemplateSection(template_id=template.id, name="Section 1", sort_order=1)
    _db.session.add(section)
    _db.session.flush()

    c1 = TemplateCriterion(
        section_id=section.id, code="MB1", title="Criterion 1",
        sort_order=1, na_allowed=False,
    )
    _db.session.add(c1)
    _db.session.flush()

    for score_val in range(5):
        _db.session.add(CriterionScoringAnchor(
            criterion_id=c1.id, score=score_val,
            description=f"Score {score_val} description",
        ))

    ev1 = CriterionEvidenceItem(criterion_id=c1.id, text="Evidence 1", sort_order=1)
    _db.session.add(ev1)
    _db.session.commit()
    return template


def _login(client, app, user):
    with app.app_context():
        token = create_session(user, ip="127.0.0.1")
    client.set_cookie("session_token", token, domain="localhost")
    return token


def _create_audit_with_scores(auditor, template, status="Draft"):
    audit = Audit(
        template_id=template.id,
        auditor_id=auditor.id,
        status=status,
        audit_date=date(2026, 1, 15),
    )
    _db.session.add(audit)
    _db.session.flush()

    sections = template.sections.order_by(TemplateSection.sort_order).all()
    for section in sections:
        criteria = section.criteria.order_by(TemplateCriterion.sort_order).all()
        for criterion in criteria:
            score = AuditScore(audit_id=audit.id, criterion_id=criterion.id)
            _db.session.add(score)
            _db.session.flush()

            for item in criterion.evidence_items.order_by(CriterionEvidenceItem.sort_order).all():
                _db.session.add(EvidenceCheckState(
                    audit_score_id=score.id, evidence_item_id=item.id, is_checked=False,
                ))

    _db.session.commit()
    _db.session.refresh(audit)
    return audit


def _make_file(filename="test.pdf", content=b"fake pdf content", content_type="application/pdf"):
    """Create a file-like object for upload testing."""
    return (io.BytesIO(content), filename)


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestFileUpload:
    """Tests for POST /audits/<id>/score/<code>/upload."""

    def test_successful_upload(self, app, client):
        """A valid PDF upload should succeed and create an attachment record."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            data = {"file": _make_file("report.pdf", b"PDF content here")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=False,
            )
            # Should redirect back to scoring form
            assert resp.status_code == 302

            # Verify attachment record created
            att = EvidenceAttachment.query.first()
            assert att is not None
            assert att.original_filename == "report.pdf"
            assert att.file_size == len(b"PDF content here")
            assert att.mime_type == "application/pdf"
            assert att.uploaded_by_id == user.id

            # Verify file exists on disk
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], att.filename)
            assert os.path.exists(filepath)

    def test_upload_png(self, app, client):
        """A valid PNG upload should succeed."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            data = {"file": _make_file("photo.png", b"PNG data")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=False,
            )
            assert resp.status_code == 302
            att = EvidenceAttachment.query.first()
            assert att is not None
            assert att.mime_type == "image/png"

    def test_upload_docx(self, app, client):
        """A valid DOCX upload should succeed."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            data = {"file": _make_file("doc.docx", b"DOCX data")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=False,
            )
            assert resp.status_code == 302
            att = EvidenceAttachment.query.first()
            assert att is not None
            assert att.original_filename == "doc.docx"

    def test_reject_invalid_file_type(self, app, client):
        """Uploading an unsupported file type should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            data = {"file": _make_file("script.exe", b"malicious")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert resp.status_code == 200  # Redirected back to form
            assert b"File type not allowed" in resp.data
            assert EvidenceAttachment.query.count() == 0

    def test_reject_txt_file(self, app, client):
        """Uploading a .txt file should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            data = {"file": _make_file("notes.txt", b"text content")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert b"File type not allowed" in resp.data
            assert EvidenceAttachment.query.count() == 0

    def test_reject_oversized_file(self, app, client):
        """Uploading a file > 20 MB should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            # Create content just over 20 MB
            big_content = b"x" * (20 * 1024 * 1024 + 1)
            data = {"file": _make_file("big.pdf", big_content)}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            # Either our validation catches it or Flask's MAX_CONTENT_LENGTH does
            assert EvidenceAttachment.query.count() == 0

    def test_reject_upload_on_completed_audit(self, app, client):
        """Uploading to a Completed audit should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Completed")
            _login(client, app, user)

            data = {"file": _make_file("report.pdf", b"PDF content")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert b"locked" in resp.data.lower()
            assert EvidenceAttachment.query.count() == 0

    def test_reject_upload_on_archived_audit(self, app, client):
        """Uploading to an Archived audit should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Archived")
            _login(client, app, user)

            data = {"file": _make_file("report.pdf", b"PDF content")}
            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert b"locked" in resp.data.lower()
            assert EvidenceAttachment.query.count() == 0

    def test_no_file_selected(self, app, client):
        """Submitting without a file should show an error."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data={},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            assert b"No file selected" in resp.data


# ---------------------------------------------------------------------------
# Deletion tests
# ---------------------------------------------------------------------------


class TestAttachmentDeletion:
    """Tests for DELETE /api/attachments/<id>."""

    def _upload_file(self, client, audit_id, code="MB1", filename="test.pdf", content=b"data"):
        """Helper to upload a file and return the attachment."""
        data = {"file": _make_file(filename, content)}
        client.post(
            f"/audits/{audit_id}/score/{code}/upload",
            data=data,
            content_type="multipart/form-data",
        )
        return EvidenceAttachment.query.order_by(EvidenceAttachment.id.desc()).first()

    def test_delete_attachment_success(self, app, client):
        """Deleting an attachment on a Draft audit should remove file and record."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Draft")
            _login(client, app, user)

            att = self._upload_file(client, audit.id)
            assert att is not None
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], att.filename)
            assert os.path.exists(filepath)

            resp = client.delete(f"/api/attachments/{att.id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["ok"] is True

            # Verify record removed
            assert EvidenceAttachment.query.get(att.id) is None
            # Verify file removed
            assert not os.path.exists(filepath)

    def test_delete_attachment_in_progress(self, app, client):
        """Deleting an attachment on an In_Progress audit should succeed."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="In_Progress")
            _login(client, app, user)

            att = self._upload_file(client, audit.id)
            resp = client.delete(f"/api/attachments/{att.id}")
            assert resp.status_code == 200
            assert resp.get_json()["ok"] is True

    def test_reject_delete_on_completed_audit(self, app, client):
        """Deleting an attachment on a Completed audit should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            # Create as Draft, upload, then change status
            audit = _create_audit_with_scores(user, template, status="Draft")
            _login(client, app, user)

            att = self._upload_file(client, audit.id)
            # Manually set audit to Completed
            audit.status = "Completed"
            _db.session.commit()

            resp = client.delete(f"/api/attachments/{att.id}")
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()
            # File and record should still exist
            assert EvidenceAttachment.query.get(att.id) is not None

    def test_reject_delete_on_archived_audit(self, app, client):
        """Deleting an attachment on an Archived audit should be rejected."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template, status="Draft")
            _login(client, app, user)

            att = self._upload_file(client, audit.id)
            audit.status = "Archived"
            _db.session.commit()

            resp = client.delete(f"/api/attachments/{att.id}")
            assert resp.status_code == 400
            assert "locked" in resp.get_json()["error"].lower()

    def test_delete_nonexistent_attachment(self, app, client):
        """Deleting a nonexistent attachment should return 404."""
        with app.app_context():
            user = _create_user()
            _login(client, app, user)

            resp = client.delete("/api/attachments/9999")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------


class TestAttachmentDownload:
    """Tests for GET /audits/<id>/score/<code>/download/<attachment_id>."""

    def test_download_attachment(self, app, client):
        """Downloading an attachment should return the file content."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            content = b"This is a test PDF file content"
            data = {"file": _make_file("report.pdf", content)}
            client.post(
                f"/audits/{audit.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
            )
            att = EvidenceAttachment.query.first()
            assert att is not None

            resp = client.get(
                f"/audits/{audit.id}/score/MB1/download/{att.id}"
            )
            assert resp.status_code == 200
            assert resp.data == content

    def test_download_nonexistent_attachment(self, app, client):
        """Downloading a nonexistent attachment should return 404."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit = _create_audit_with_scores(user, template)
            _login(client, app, user)

            resp = client.get(f"/audits/{audit.id}/score/MB1/download/9999")
            assert resp.status_code == 404

    def test_download_wrong_audit(self, app, client):
        """Downloading an attachment from the wrong audit should return 404."""
        with app.app_context():
            user = _create_user()
            template = _create_template()
            audit1 = _create_audit_with_scores(user, template)
            audit2 = _create_audit_with_scores(user, template)
            _login(client, app, user)

            # Upload to audit1
            data = {"file": _make_file("report.pdf", b"content")}
            client.post(
                f"/audits/{audit1.id}/score/MB1/upload",
                data=data,
                content_type="multipart/form-data",
            )
            att = EvidenceAttachment.query.first()

            # Try to download from audit2
            resp = client.get(
                f"/audits/{audit2.id}/score/MB1/download/{att.id}"
            )
            assert resp.status_code == 404
