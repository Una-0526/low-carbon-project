from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PointTransaction(Base):
    """积分流水表：所有积分变动都留痕（打卡入账 / 连续奖励 / 未来的兑换扣减等）。"""

    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    points: Mapped[int] = mapped_column(Integer)  # 正数入账，预留负数（兑换）
    reason: Mapped[str] = mapped_column(String(20), index=True)  # checkin / streak_bonus / ...
    checkin_id: Mapped[int | None] = mapped_column(ForeignKey("checkins.id"), default=None)
    description: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    user = relationship("User")
