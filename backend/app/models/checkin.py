from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Checkin(Base):
    """学生绿色打卡记录。"""

    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(20))  # 骑行/随手关灯/光盘/自带水杯/爬楼
    photo_path: Mapped[str | None] = mapped_column(String(200), default=None)  # /uploads/xxx.jpg
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)

    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending/approved/rejected
    ai_flagged: Mapped[bool] = mapped_column(Boolean, default=False)  # AI 防作弊标记
    ai_flags: Mapped[str] = mapped_column(String(500), default="")  # JSON 数组：命中规则说明
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)  # 审核通过后入账积分
    review_reason: Mapped[str | None] = mapped_column(String(200), default=None)  # 教师驳回原因

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    user = relationship("User")
