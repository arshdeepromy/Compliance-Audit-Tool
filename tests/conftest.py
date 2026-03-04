"""Shared test fixtures for the Tōtika Audit application."""

import os
import tempfile
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models.user import User, Session
from app.utils.auth import hash_password

from tests.factories import (
    init_factories,
    UserFactory,
    AuditTemplateFactory,
    AuditFactory,
    AuditScoreFactory,
    CorrectiveActionFactory,
)


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create a Flask application configured for testing (session-scoped)."""
    db_path = tmp_path_factory.mktemp("data") / "test.db"

    class FileTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    application = create_app(config_class=FileTestConfig, run_startup=False)
    return application


@pytest.fixture(autouse=True)
def setup_db(app):
    """Create all tables before each test and drop them after."""
    with app.app_context():
        _db.create_all()
        init_factories(_db.session)
        yield
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Provide the SQLAlchemy session within an app context."""
    with app.app_context():
        yield _db.session


@pytest.fixture
def sample_user(app):
    """Create and return a sample active user."""
    with app.app_context():
        user = User(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password_hash=hash_password("correct-password"),
            roles="auditor",
            is_active=True,
        )
        _db.session.add(user)
        _db.session.commit()
        _db.session.refresh(user)
        yield user


# ---------------------------------------------------------------------------
# Factory Boy convenience fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory(app):
    """Return the UserFactory class (session already bound via setup_db)."""
    return UserFactory


@pytest.fixture
def audit_template_factory(app):
    """Return the AuditTemplateFactory class."""
    return AuditTemplateFactory


@pytest.fixture
def audit_factory(app):
    """Return the AuditFactory class."""
    return AuditFactory


@pytest.fixture
def audit_score_factory(app):
    """Return the AuditScoreFactory class."""
    return AuditScoreFactory


@pytest.fixture
def corrective_action_factory(app):
    """Return the CorrectiveActionFactory class."""
    return CorrectiveActionFactory
