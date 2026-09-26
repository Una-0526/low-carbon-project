"""低碳行为业务逻辑层。"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CarbonActivity
from app.schemas import CarbonActivityCreate


def create_activity(db: Session, data: CarbonActivityCreate, user) -> CarbonActivity:
    """username / role 取自登录用户，而不是请求体。"""
    activity = CarbonActivity(
        username=user.username,
        role=user.role,
        activity_type=data.activity_type,
        carbon_saved_kg=data.carbon_saved_kg,
        description=data.description,
        created_at=datetime.now(),
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def list_activities(
    db: Session,
    role: str | None = None,
    username: str | None = None,
    limit: int = 100,
) -> list[CarbonActivity]:
    stmt = select(CarbonActivity).order_by(CarbonActivity.created_at.desc()).limit(limit)
    if role:
        stmt = stmt.where(CarbonActivity.role == role)
    if username:
        stmt = stmt.where(CarbonActivity.username == username)
    return list(db.scalars(stmt))


def get_stats(db: Session) -> dict:
    total_records = db.scalar(select(func.count(CarbonActivity.id))) or 0
    total_saved = db.scalar(select(func.coalesce(func.sum(CarbonActivity.carbon_saved_kg), 0.0))) or 0.0

    by_role_rows = db.execute(
        select(CarbonActivity.role, func.coalesce(func.sum(CarbonActivity.carbon_saved_kg), 0.0))
        .group_by(CarbonActivity.role)
    ).all()
    by_type_rows = db.execute(
        select(CarbonActivity.activity_type, func.coalesce(func.sum(CarbonActivity.carbon_saved_kg), 0.0))
        .group_by(CarbonActivity.activity_type)
    ).all()

    return {
        "total_records": total_records,
        "total_carbon_saved_kg": float(total_saved),
        "carbon_saved_by_role": {role: float(v) for role, v in by_role_rows},
        "carbon_saved_by_type": {t: float(v) for t, v in by_type_rows},
    }
