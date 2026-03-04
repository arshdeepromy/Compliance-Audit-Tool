"""Factory Boy factories for Tōtika Audit test models."""

from datetime import date, datetime

import factory

from app.extensions import db
from app.models.user import User
from app.models.template import AuditTemplate, TemplateSection, TemplateCriterion
from app.models.audit import Audit, AuditScore
from app.models.action import CorrectiveAction
from app.utils.auth import hash_password


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory wired to the test SQLAlchemy session."""

    class Meta:
        abstract = True
        sqlalchemy_session = None  # set at runtime via init_factories()
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.Sequence(lambda n: f"User {n}")
    password_hash = factory.LazyAttribute(lambda _: hash_password("password123"))
    roles = "auditor"
    is_active = True


class AuditTemplateFactory(BaseFactory):
    class Meta:
        model = AuditTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    version = "1.0"
    is_active = True
    is_builtin = False


class TemplateSectionFactory(BaseFactory):
    class Meta:
        model = TemplateSection

    template = factory.SubFactory(AuditTemplateFactory)
    name = factory.Sequence(lambda n: f"Section {n}")
    sort_order = factory.Sequence(lambda n: n)


class TemplateCriterionFactory(BaseFactory):
    class Meta:
        model = TemplateCriterion

    section = factory.SubFactory(TemplateSectionFactory)
    code = factory.Sequence(lambda n: f"MB{n}")
    title = factory.Sequence(lambda n: f"Criterion {n}")
    sort_order = factory.Sequence(lambda n: n)


class AuditFactory(BaseFactory):
    class Meta:
        model = Audit

    template = factory.SubFactory(AuditTemplateFactory)
    auditor = factory.SubFactory(UserFactory)
    status = "Draft"
    audit_date = factory.LazyFunction(date.today)
    assessment_period = "2024-Q1"
    overall_score = None


class AuditScoreFactory(BaseFactory):
    class Meta:
        model = AuditScore

    audit = factory.SubFactory(AuditFactory)
    criterion = factory.SubFactory(TemplateCriterionFactory)
    score = None
    is_na = False
    na_reason = None
    notes = None


class CorrectiveActionFactory(BaseFactory):
    class Meta:
        model = CorrectiveAction

    audit = factory.SubFactory(AuditFactory)
    criterion_code = factory.Sequence(lambda n: f"MB{n}")
    description = factory.Sequence(lambda n: f"Action item {n}")
    assigned_to = factory.SubFactory(UserFactory)
    priority = "high"
    status = "Open"
    due_date = factory.LazyFunction(date.today)


# All factory classes for easy iteration
ALL_FACTORIES = [
    UserFactory,
    AuditTemplateFactory,
    TemplateSectionFactory,
    TemplateCriterionFactory,
    AuditFactory,
    AuditScoreFactory,
    CorrectiveActionFactory,
]


def init_factories(session):
    """Bind all factories to the given SQLAlchemy session."""
    for factory_cls in ALL_FACTORIES:
        factory_cls._meta.sqlalchemy_session = session
