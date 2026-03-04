"""Property-based tests for Legacy JSON Import, Export, and Seed Data.

Feature: totika-audit-webapp
Property 31: Legacy JSON import/export round-trip
Property 32: Malformed JSON import returns specific errors
Property 33: Seed import is idempotent

Uses Hypothesis for property-based testing with the Flask application context.
"""

import itertools
import json
import os

import pytest
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from app import create_app
from app.config import TestConfig
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

_counter = itertools.count()


def _uid():
    return next(_counter)


def _make_app(tmp_path):
    """Create a fresh Flask app with its own SQLite DB."""
    uid = _uid()

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / f'import_pbt_{uid}.db'}"

    app = create_app(config_class=LocalTestConfig, run_startup=False)
    with app.app_context():
        db.create_all()
    return app


def _create_user(app, username=None, roles="auditor"):
    """Create a test user inside app context."""
    uid = _uid()
    uname = username or f"user_{uid}"
    with app.app_context():
        user = User(
            username=uname,
            email=f"{uname}@test.com",
            display_name=f"Test {uname}",
            password_hash=hash_password("password"),
            roles=roles,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user.id


def _create_template(app, num_criteria=3):
    """Create a minimal built-in template with criteria and evidence items."""
    with app.app_context():
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

            for score in range(5):
                db.session.add(
                    CriterionScoringAnchor(
                        criterion_id=criterion.id,
                        score=score,
                        description=f"Score {score} description",
                    )
                )

            for j in range(2):
                db.session.add(
                    CriterionEvidenceItem(
                        criterion_id=criterion.id,
                        text=f"Evidence item {j}",
                        sort_order=j,
                    )
                )

        db.session.commit()
        return template.id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_date_strategy = st.dates(
    min_value=__import__("datetime").date(2020, 1, 1),
    max_value=__import__("datetime").date(2030, 12, 31),
)

_score_strategy = st.one_of(st.none(), st.integers(min_value=0, max_value=4))

_notes_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=0,
    max_size=100,
)

_priority_strategy = st.sampled_from(["critical", "high", "medium"])
_action_status_strategy = st.sampled_from(["Open", "In_Progress", "Completed", "Overdue"])


def _legacy_score_entry(evidence_count=2):
    """Strategy for a single score entry in legacy JSON."""
    return st.fixed_dictionaries({
        "score": _score_strategy,
        "notes": _notes_strategy,
        "evidence": st.fixed_dictionaries({}),
    })


def _gap_item_strategy(criterion_codes):
    """Strategy for a single gap item."""
    return st.fixed_dictionaries({
        "criterion_code": st.sampled_from(criterion_codes),
        "description": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=80,
        ),
        "priority": _priority_strategy,
        "status": _action_status_strategy,
        "due_date": _date_strategy.map(lambda d: d.isoformat()),
        "assigned_to": st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=0,
            max_size=30,
        ),
    })


def _valid_legacy_json_strategy(num_criteria=3):
    """Strategy that generates valid legacy JSON dicts."""
    codes = [f"MB{i}" for i in range(1, num_criteria + 1)]

    return st.fixed_dictionaries({
        "meta": st.fixed_dictionaries({
            "assessor": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=50,
            ),
            "auditee": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=50,
            ),
            "date": _date_strategy.map(lambda d: d.isoformat()),
            "period": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                min_size=1,
                max_size=30,
            ),
            "nextReview": _date_strategy.map(lambda d: d.isoformat()),
        }),
        "scores": st.fixed_dictionaries({
            code: _legacy_score_entry() for code in codes
        }),
        "gapItems": st.lists(
            _gap_item_strategy(codes), min_size=0, max_size=3
        ),
    })


# ---------------------------------------------------------------------------
# Property 31: Legacy JSON import/export round-trip
# ---------------------------------------------------------------------------


class TestProperty31LegacyJsonRoundTrip:
    """**Validates: Requirements 17.1, 17.3, 17.4**

    For any valid legacy JSON file (containing meta, scores with MB1–MB54,
    and optionally gapItems), importing then exporting SHALL produce a
    data-equivalent JSON representation preserving all scores, notes,
    evidence checked states, and metadata.
    """

    @given(data=_valid_legacy_json_strategy(num_criteria=5))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_round_trip_preserves_scores(self, tmp_path, data):
        """Import then export preserves score values for every criterion."""
        app = _make_app(tmp_path)
        user_id = _create_user(app)
        _create_template(app, num_criteria=5)

        with app.app_context():
            audit = import_legacy_json(data, user_id)
            exported = export_to_legacy_json(audit.id)

        # Every criterion score in the input should match the export
        for code, entry in data["scores"].items():
            assert code in exported["scores"], f"Missing criterion {code} in export"
            exported_score = exported["scores"][code]["score"]
            input_score = entry["score"]
            if input_score is not None and 0 <= input_score <= 4:
                assert exported_score == input_score, (
                    f"Score mismatch for {code}: input={input_score}, exported={exported_score}"
                )
            else:
                assert exported_score is None

    @given(data=_valid_legacy_json_strategy(num_criteria=5))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_round_trip_preserves_notes(self, tmp_path, data):
        """Import then export preserves notes for every criterion."""
        app = _make_app(tmp_path)
        user_id = _create_user(app)
        _create_template(app, num_criteria=5)

        with app.app_context():
            audit = import_legacy_json(data, user_id)
            exported = export_to_legacy_json(audit.id)

        for code, entry in data["scores"].items():
            input_notes = entry.get("notes", "")
            exported_notes = exported["scores"][code]["notes"]
            # The importer stores empty string as None, export converts None to ""
            assert exported_notes == (input_notes or ""), (
                f"Notes mismatch for {code}: input={input_notes!r}, exported={exported_notes!r}"
            )

    @given(data=_valid_legacy_json_strategy(num_criteria=5))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_round_trip_preserves_metadata(self, tmp_path, data):
        """Import then export preserves audit metadata (date, period, nextReview)."""
        app = _make_app(tmp_path)
        user_id = _create_user(app)
        _create_template(app, num_criteria=5)

        with app.app_context():
            audit = import_legacy_json(data, user_id)
            exported = export_to_legacy_json(audit.id)

        assert exported["meta"]["date"] == data["meta"]["date"]
        assert exported["meta"]["period"] == data["meta"]["period"]
        assert exported["meta"]["nextReview"] == data["meta"]["nextReview"]

    @given(data=_valid_legacy_json_strategy(num_criteria=5))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_round_trip_preserves_gap_items(self, tmp_path, data):
        """Import then export preserves corrective action / gap item data."""
        app = _make_app(tmp_path)
        user_id = _create_user(app)
        _create_template(app, num_criteria=5)

        with app.app_context():
            audit = import_legacy_json(data, user_id)
            exported = export_to_legacy_json(audit.id)

        input_gaps = data.get("gapItems", [])
        exported_gaps = exported.get("gapItems", [])
        assert len(exported_gaps) == len(input_gaps)

        for i, (inp, exp) in enumerate(zip(input_gaps, exported_gaps)):
            assert exp["criterion_code"] == inp["criterion_code"], f"gapItems[{i}] criterion_code mismatch"
            assert exp["description"] == inp["description"], f"gapItems[{i}] description mismatch"
            assert exp["priority"] == inp["priority"], f"gapItems[{i}] priority mismatch"
            assert exp["status"] == inp["status"], f"gapItems[{i}] status mismatch"
            assert exp["due_date"] == inp["due_date"], f"gapItems[{i}] due_date mismatch"


# ---------------------------------------------------------------------------
# Property 32: Malformed JSON import returns specific errors
# ---------------------------------------------------------------------------


class TestProperty32MalformedJsonImportErrors:
    """**Validates: Requirements 17.2**

    For any JSON file that is malformed or missing required fields (meta,
    scores), the import SHALL be rejected with a response listing the
    specific validation failures.
    """

    @given(
        has_meta=st.booleans(),
        has_scores=st.booleans(),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_missing_required_fields_produces_errors(self, has_meta, has_scores):
        """Omitting meta and/or scores produces specific validation errors."""
        # At least one field must be missing for this to be meaningful
        assume(not (has_meta and has_scores))

        data: dict = {}
        if has_meta:
            data["meta"] = {
                "assessor": "A",
                "auditee": "B",
                "date": "2025-01-01",
                "period": "Q1",
                "nextReview": "2025-06-01",
            }
        if has_scores:
            data["scores"] = {"MB1": {"score": 3, "notes": "", "evidence": {}}}

        errors = validate_legacy_json(data)
        assert len(errors) > 0, "Expected validation errors for incomplete data"

        if not has_meta:
            assert any("meta" in e.lower() for e in errors), (
                f"Expected error about missing 'meta', got: {errors}"
            )
        if not has_scores:
            assert any("scores" in e.lower() for e in errors), (
                f"Expected error about missing 'scores', got: {errors}"
            )

    @given(
        bad_score=st.integers().filter(lambda x: x < 0 or x > 4),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_invalid_score_values_produce_errors(self, bad_score):
        """Scores outside 0–4 produce specific validation errors."""
        data = {
            "meta": {
                "assessor": "A",
                "auditee": "B",
                "date": "2025-01-01",
                "period": "Q1",
                "nextReview": "2025-06-01",
            },
            "scores": {
                "MB1": {"score": bad_score, "notes": "", "evidence": {}},
            },
        }
        errors = validate_legacy_json(data)
        assert len(errors) > 0, "Expected validation errors for invalid score"
        assert any("score" in e.lower() and "MB1" in e for e in errors), (
            f"Expected error about invalid score for MB1, got: {errors}"
        )

    @given(
        bad_date=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        ).filter(lambda s: not _is_valid_date(s)),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_invalid_date_format_produces_errors(self, bad_date):
        """Invalid date formats in meta.date produce specific errors."""
        data = {
            "meta": {
                "assessor": "A",
                "auditee": "B",
                "date": bad_date,
                "period": "Q1",
                "nextReview": "2025-06-01",
            },
            "scores": {"MB1": {"score": 3, "notes": "", "evidence": {}}},
        }
        errors = validate_legacy_json(data)
        assert len(errors) > 0, "Expected validation errors for invalid date"
        assert any("date" in e.lower() for e in errors), (
            f"Expected error about invalid date, got: {errors}"
        )

    def test_non_dict_data_returns_error(self):
        """Non-dict input returns a validation error."""
        errors = validate_legacy_json("not a dict")
        assert len(errors) > 0
        assert any("object" in e.lower() for e in errors)

    def test_meta_as_non_dict_returns_error(self):
        """meta field as non-dict returns a validation error."""
        data = {"meta": "not a dict", "scores": {}}
        errors = validate_legacy_json(data)
        assert len(errors) > 0
        assert any("meta" in e.lower() for e in errors)

    def test_scores_as_non_dict_returns_error(self):
        """scores field as non-dict returns a validation error."""
        data = {
            "meta": {"assessor": "A", "auditee": "B", "date": "2025-01-01", "period": "Q1"},
            "scores": "not a dict",
        }
        errors = validate_legacy_json(data)
        assert len(errors) > 0
        assert any("scores" in e.lower() for e in errors)


def _is_valid_date(s: str) -> bool:
    """Check if a string is a valid ISO date."""
    from datetime import date
    try:
        date.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Property 33: Seed import is idempotent
# ---------------------------------------------------------------------------


class TestProperty33SeedImportIdempotent:
    """**Validates: Requirements 17.7**

    For any seed data directory, running the seed import process multiple
    times SHALL NOT create duplicate audit records. Previously imported
    files (tracked by filename) SHALL be skipped.
    """

    @given(
        num_files=st.integers(min_value=1, max_value=3),
        num_runs=st.integers(min_value=2, max_value=4),
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_multiple_seed_runs_no_duplicates(self, tmp_path, num_files, num_runs):
        """Running load_seed_data N times creates exactly num_files audits."""
        app = _make_app(tmp_path)

        # Create a unique seed directory per example to avoid cross-contamination
        uid = _uid()
        seed_dir = tmp_path / f"seed_data_{uid}"
        seed_dir.mkdir(exist_ok=True)

        for i in range(num_files):
            seed_json = {
                "meta": {
                    "assessor": f"Assessor {i}",
                    "auditee": f"Auditee {i}",
                    "date": f"2025-0{(i % 9) + 1}-15",
                    "period": f"Q{(i % 4) + 1} 2025",
                    "nextReview": f"2025-{((i + 6) % 12) + 1:02d}-15",
                },
                "scores": {
                    f"MB{j}": {"score": j % 5, "notes": f"Note {j}", "evidence": {}}
                    for j in range(1, 4)
                },
                "gapItems": [],
            }
            (seed_dir / f"audit_{i}.json").write_text(
                json.dumps(seed_json), encoding="utf-8"
            )

        app.config["SEED_DATA_DIR"] = str(seed_dir)

        with app.app_context():
            # Create template and admin user needed for seed import
            _create_template_in_context(num_criteria=3)
            _create_admin_user_in_context()

            # Run seed import multiple times
            for _ in range(num_runs):
                load_seed_data(app)

            # Verify: exactly num_files audits created (no duplicates)
            audit_count = Audit.query.count()
            assert audit_count == num_files, (
                f"Expected {num_files} audits after {num_runs} runs, got {audit_count}"
            )

            # Verify: exactly num_files tracker entries
            tracker_count = SeedFileTracker.query.count()
            assert tracker_count == num_files, (
                f"Expected {num_files} tracker entries, got {tracker_count}"
            )

    @given(num_runs=st.integers(min_value=2, max_value=4))
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_seed_tracker_prevents_reimport(self, tmp_path, num_runs):
        """Files already tracked in SeedFileTracker are skipped on re-run."""
        app = _make_app(tmp_path)

        uid = _uid()
        seed_dir = tmp_path / f"seed_data_{uid}"
        seed_dir.mkdir(exist_ok=True)

        seed_json = {
            "meta": {
                "assessor": "A",
                "auditee": "B",
                "date": "2025-03-15",
                "period": "Q1 2025",
                "nextReview": "2025-09-15",
            },
            "scores": {
                f"MB{j}": {"score": 3, "notes": "", "evidence": {}}
                for j in range(1, 4)
            },
            "gapItems": [],
        }
        (seed_dir / "single_audit.json").write_text(
            json.dumps(seed_json), encoding="utf-8"
        )

        app.config["SEED_DATA_DIR"] = str(seed_dir)

        with app.app_context():
            _create_template_in_context(num_criteria=3)
            _create_admin_user_in_context()

            # First run — should import
            load_seed_data(app)
            first_run_count = Audit.query.count()
            assert first_run_count == 1

            # Subsequent runs — should skip
            for _ in range(num_runs - 1):
                load_seed_data(app)

            final_count = Audit.query.count()
            assert final_count == 1, (
                f"Expected 1 audit after {num_runs} runs, got {final_count}"
            )


# ---------------------------------------------------------------------------
# In-context helpers (used inside app.app_context())
# ---------------------------------------------------------------------------


def _create_template_in_context(num_criteria=3):
    """Create a built-in template (must be called inside app_context)."""
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

        for score in range(5):
            db.session.add(
                CriterionScoringAnchor(
                    criterion_id=criterion.id,
                    score=score,
                    description=f"Score {score} description",
                )
            )

        for j in range(2):
            db.session.add(
                CriterionEvidenceItem(
                    criterion_id=criterion.id,
                    text=f"Evidence item {j}",
                    sort_order=j,
                )
            )

    db.session.commit()
    return template.id


def _create_admin_user_in_context():
    """Create an admin user (must be called inside app_context)."""
    user = User(
        username="admin",
        email="admin@test.com",
        display_name="Admin User",
        password_hash=hash_password("admin"),
        roles="admin",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user.id
