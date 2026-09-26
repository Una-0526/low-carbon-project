"""积分流水服务：所有积分变动统一走这里，保证留痕。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PointTransaction


def credit(
    db: Session,
    user_id: int,
    points: int,
    reason: str,
    checkin_id: int | None = None,
    description: str | None = None,
) -> PointTransaction:
    """记一笔积分流水（不提交事务，由调用方统一 commit）。"""
    tx = PointTransaction(
        user_id=user_id,
        points=points,
        reason=reason,
        checkin_id=checkin_id,
        description=description,
    )
    db.add(tx)
    return tx


def total(db: Session, user_id: int) -> int:
    """用户累计可用积分。"""
    return int(
        db.scalar(
            select(func.coalesce(func.sum(PointTransaction.points), 0)).where(
                PointTransaction.user_id == user_id
            )
        )
        or 0
    )


def list_transactions(db: Session, user_id: int, limit: int = 100) -> list[PointTransaction]:
    rows = db.scalars(
        select(PointTransaction)
        .where(PointTransaction.user_id == user_id)
        .order_by(PointTransaction.created_at.desc(), PointTransaction.id.desc())
        .limit(limit)
    ).all()
    return list(rows)
