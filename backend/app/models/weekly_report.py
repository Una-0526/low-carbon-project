from datetime import date, datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyReport(Base):
    """学生碳周报快照：每周一自动生成上一周的汇总（首次访问时惰性补齐）。

    减碳量 / 打卡次数来自当周已通过打卡，积分来自当周正数流水；
    rank 为当周全校减碳量排名（仅当周有打卡的学生参与）。
    """

    __tablename__ = "weekly_reports"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_weekly_user_week"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(index=True)  # 学生
    week_start: Mapped[date] = mapped_column(index=True)  # 周一日期
    carbon_kg: Mapped[float] = mapped_column(Float, default=0.0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    checkin_count: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int | None] = mapped_column(Integer, default=None)
    rank_change: Mapped[int | None] = mapped_column(Integer, default=None)  # 正升负降
    summary: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
