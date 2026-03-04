"""Unit tests for the legacy JSON import/export service."""

import json

import pytest

from app.extensions import db
from app.models.action import CorrectiveAction
from app.models.audit import Audit, AuditScore, EvidenceCheckState
from app.models.log import SeedFileTracker
from app.models.template import (
    AuditTemplate,
    CriterionEvidenceItem,
    CriterionScoringAnchor,
    TemplateCriterion,
    TemplateSection,
)
from app.models.user import User
from app.services.importer import (
    export_to_legacy_json,
    import_legacy_json,
    load_seed_data,
    validate_legacy_json,
)
from app.utils.auth import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(username="testuser", roles="auditor"):
    """Create and return a test user."""
    user = User(
        username=username,
        email=f"{username}@test.com",
        display_name=f"Test {username}",
        password_hash=hash_password("password"),
        roles=roles,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


def _create_template(num_criteria=3):
    """Create a minimal built-in template with criteria and evidence items."""
    template = AuditTemplate(
        name="Tōtika Category 2",
        version="1.0",
        is_active=True,
        is_builtin=True,
    )
    db.session.add(template)
    db.session.flush()

    section = TemplateSection(
        template_id=template.id, name="Section 1", sort_order=0
    )
    db.session.add(section)
    db.session.flush()

    for i in range(1, num_criteria + 1):
        criterion = TemplateCriterion(
            section_id=section.id,
            code=f"MB{i}",
            title=f"Criterion {i}",
            sort_order=i,
        )
        db.session.add(criterion)
        db.session.flush()

        # Add scoring anchors
        for score in range(5):
            db.session.add(
                CriterionScoringAnchor(
                    criterion_id=criterion.id,
                    score=score,
                    description=f"Score {score} description",
                )
            )

        # Add evidence items
        for j in range(2):
            db.session.add(
                CriterionEvidenceItem(
                    criterion_id=criterion.id,
                    text=f"Evidence item {j}",
                    sort_order=j,
                )
            )

    db.session.commit()
    return template


def _make_valid_legacy_json(num_criteria=3):
    """Return a valid legacy JSON dict."""
    scores = {}
    for i in range(1, num_criteria + 1):
        scores[f"MB{i}"] = {
            "score": min(i, 4),
            "notes": f"Notes for MB{i}",
            "evidence": {},
        }
    return {
        "meta": {
            "assessor": "John Doe",
            "auditee": "Jane Smith",
            "date": "2025-06-15",
            "period": "Q2 2025",
            "nextReview": "2025-12-15",
        },
        "scores": scores,
        "gapItems": [
            {
                "criterion_code": "MB1",
                "description": "Fix the policy",
                "priority": "critical",
                "status": "Open",
                "due_date": "2025-07-01",
                "assigned_to": "Someone",
            }
        ],
    }


# ---------------------------------------------------------------------------
# validate_legacy_json tests
# ---------------------------------------------------------------------------


class TestValidateLegacyJson:
    """Tests for validate_legacy_json."""

    def test_valid_data_returns_no_errors(self):
        data = _make_valid_legacy_json()
        errors = validate_legacy_json(data)
        assert errors == []

    def test_missing_meta(self):
        data = {"scores": {"MB1": {"score": 3}}}
        errors = validate_legacy_json(data)
        assert any("meta" in e for e in errors)

    def test_missing_scores(self):
        data = {"meta": {"date": "2025-01-01"}}
        errors = validate_legacy_json(data)
        assert any("scores" in e for e in errors)

    def test_invalid_score_value(self):
        data = {
            "meta": {"date": "2025-01-01"},
            "scores": {"MB1": {"score": 5}},
        }
        errors = validate_legacy_json(data)
        assert any("Invalid score" in e for e in errors)

    def test_invalid_date_format(self):
        data = {
            "meta": {"date": "not-a-date"},
            "scores": {"MB1": {"score": 3}},
        }
        errors = validate_legacy_json(data)
        assert any("date" in e.lower() for e in errors)

    def test_invalid_gap_item_priority(self):
        data = _make_valid_legacy_json()
        data["gapItems"] = [
            {
                "criterion_code": "MB1",
                "description": "Fix it",
                "priority": "invalid",
            }
        ]
        errors = validate_legacy_json(data)
        assert any("priority" in e for e in errors)

    def test_non_dict_data(self):
        errors = validate_legacy_json("not a dict")
        assert errors == ["Data must be a JSON object"]

    def test_null_score_is_valid(self):
        data = {
            "meta": {"date": "2025-01-01"},
            "scores": {"MB1": {"score": None, "notes": ""}},
        }
        errors = validate_legacy_json(data)
        assert errors == []

    def test_missing_gap_item_fields(self):
        data = _make_valid_legacy_json()
        data["gapItems"] = [{"priority": "high"}]
        errors = validate_legacy_json(data)
        assert any("criterion_code" in e for e in errors)
        assert any("description" in e for e in errors)


# ---------------------------------------------------------------------------
# import_legacy_json tests
# ---------------------------------------------------------------------------


class TestImportLegacyJson:
    """Tests for import_legacy_json."""

    def test_basic_import(self, app):
        with app.app_context():
            template = _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)

            assert audit.id is not None
            assert audit.status == "Completed"
            assert audit.audit_date is not None
            assert str(audit.audit_date) == "2025-06-15"
            assert audit.assessment_period == "Q2 2025"
            assert audit.template_id == template.id

    def test_scores_are_persisted(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)

            scores = AuditScore.query.filter_by(audit_id=audit.id).all()
            assert len(scores) == 3
            scored = [s for s in scores if s.score is not None]
            assert len(scored) == 3

    def test_corrective_actions_created(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)

            actions = CorrectiveAction.query.filter_by(audit_id=audit.id).all()
            assert len(actions) == 1
            assert actions[0].criterion_code == "MB1"
            assert actions[0].priority == "critical"
            assert actions[0].status == "Open"

    def test_overall_score_calculated(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)

            assert audit.overall_score is not None
            # MB1=1, MB2=2, MB3=3 → avg = 2.0
            assert abs(audit.overall_score - 2.0) < 0.01

    def test_import_with_custom_status(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id, status="Draft")
            assert audit.status == "Draft"

    def test_import_records_source_filename(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(
                data, user.id, source_filename="test.json"
            )
            assert audit.imported_from == "test.json"

    def test_no_template_raises_error(self, app):
        with app.app_context():
            user = _create_user()
            data = _make_valid_legacy_json()

            with pytest.raises(ValueError, match="No active built-in template"):
                import_legacy_json(data, user.id)


# ---------------------------------------------------------------------------
# export_to_legacy_json tests
# ---------------------------------------------------------------------------


class TestExportToLegacyJson:
    """Tests for export_to_legacy_json."""

    def test_basic_export(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            assert "meta" in exported
            assert "scores" in exported
            assert "gapItems" in exported

    def test_export_preserves_scores(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            for code in ["MB1", "MB2", "MB3"]:
                assert code in exported["scores"]
                orig_score = data["scores"][code]["score"]
                assert exported["scores"][code]["score"] == orig_score

    def test_export_preserves_metadata(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            assert exported["meta"]["date"] == "2025-06-15"
            assert exported["meta"]["period"] == "Q2 2025"
            assert exported["meta"]["nextReview"] == "2025-12-15"

    def test_export_preserves_gap_items(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            assert len(exported["gapItems"]) == 1
            gap = exported["gapItems"][0]
            assert gap["criterion_code"] == "MB1"
            assert gap["description"] == "Fix the policy"
            assert gap["priority"] == "critical"

    def test_export_nonexistent_audit_raises(self, app):
        with app.app_context():
            with pytest.raises(ValueError, match="not found"):
                export_to_legacy_json(99999)


# ---------------------------------------------------------------------------
# Round-trip test
# ---------------------------------------------------------------------------


class TestImportExportRoundTrip:
    """Test that import → export preserves data."""

    def test_round_trip_scores(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            # Scores should match
            for code in data["scores"]:
                assert exported["scores"][code]["score"] == data["scores"][code]["score"]
                assert exported["scores"][code]["notes"] == data["scores"][code]["notes"]

    def test_round_trip_metadata(self, app):
        with app.app_context():
            _create_template()
            user = _create_user()
            data = _make_valid_legacy_json()

            audit = import_legacy_json(data, user.id)
            exported = export_to_legacy_json(audit.id)

            assert exported["meta"]["date"] == data["meta"]["date"]
            assert exported["meta"]["period"] == data["meta"]["period"]
            assert exported["meta"]["nextReview"] == data["meta"]["nextReview"]


# ---------------------------------------------------------------------------
# Seed data loading tests
# ---------------------------------------------------------------------------


class TestSeedDataLoading:
    """Tests for load_seed_data."""

    def test_seed_import_creates_audit(self, app, tmp_path):
        with app.app_context():
            _create_template()
            _create_user("admin", "admin")

            # Create a seed file
            seed_dir = tmp_path / "seeds"
            seed_dir.mkdir()
            data = _make_valid_legacy_json()
            seed_file = seed_dir / "test-audit.json"
            seed_file.write_text(json.dumps(data))

            app.config["SEED_DATA_DIR"] = str(seed_dir)
            load_seed_data(app)

            # Verify audit was created
            audits = Audit.query.all()
            assert len(audits) == 1
            assert audits[0].status == "Completed"
            assert audits[0].imported_from == "test-audit.json"

            # Verify tracker was created
            tracker = SeedFileTracker.query.filter_by(
                filename="test-audit.json"
            ).first()
            assert tracker is not None
            assert tracker.audit_id == audits[0].id

    def test_seed_import_is_idempotent(self, app, tmp_path):
        with app.app_context():
            _create_template()
            _create_user("admin", "admin")

            seed_dir = tmp_path / "seeds"
            seed_dir.mkdir()
            data = _make_valid_legacy_json()
            (seed_dir / "test.json").write_text(json.dumps(data))

            app.config["SEED_DATA_DIR"] = str(seed_dir)

            # Import twice
            load_seed_data(app)
            load_seed_data(app)

            # Should only have one audit
            audits = Audit.query.all()
            assert len(audits) == 1

    def test_seed_skips_invalid_json(self, app, tmp_path):
        with app.app_context():
            _create_template()
            _create_user("admin", "admin")

            seed_dir = tmp_path / "seeds"
            seed_dir.mkdir()
            (seed_dir / "bad.json").write_text("{invalid json")

            app.config["SEED_DATA_DIR"] = str(seed_dir)
            load_seed_data(app)

            assert Audit.query.count() == 0

    def test_seed_skips_missing_directory(self, app):
        with app.app_context():
            app.config["SEED_DATA_DIR"] = "/nonexistent/path"
            # Should not raise
            load_seed_data(app)
