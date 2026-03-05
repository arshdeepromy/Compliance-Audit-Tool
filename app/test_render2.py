"""Debug the gap items query."""
from app import create_app
from app.extensions import db
from app.models.audit import Audit, AuditScore
from app.models.action import CorrectiveAction
from app.models.template import TemplateCriterion, TemplateSection

app = create_app()
with app.app_context():
    audit = db.session.get(Audit, 5)
    gap_scores = (
        AuditScore.query
        .filter_by(audit_id=5)
        .filter(AuditScore.score.in_([0, 1, 2]))
        .join(TemplateCriterion, AuditScore.criterion_id == TemplateCriterion.id)
        .add_columns(TemplateCriterion.code, TemplateCriterion.title)
        .all()
    )
    print(f"Gap scores: {len(gap_scores)}")
    for audit_score_obj, code, title in gap_scores[:5]:
        actions = CorrectiveAction.query.filter_by(audit_id=5, criterion_code=code).all()
        print(f"  {code}: score={audit_score_obj.score}, actions={len(actions)}")
        for a in actions[:2]:
            print(f"    Action {a.id}: {a.description[:60]}...")
