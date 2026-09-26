from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CarbonActivity(Base):
    """低碳行为记录：一次绿色出行 / 节能行为所减少的碳排放。"""

    __tablename__ = "carbon_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(10))  # student / teacher
    activity_type: Mapped[str] = mapped_column(String(30))  # 如：步行、骑行、公交
    carbon_saved_kg: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
