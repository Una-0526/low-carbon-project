from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RewardItem(Base):
    """积分商城商品：教师可上下架、调整所需积分与库存。"""

    __tablename__ = "reward_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[str] = mapped_column(String(20))  # 食堂 / 超市 / 文具
    points_cost: Mapped[int] = mapped_column(Integer)  # 所需积分
    stock: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # 上架 / 下架
    description: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Redemption(Base):
    """兑换记录：快照商品名与积分，商品后续修改不影响历史记录。"""

    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("reward_items.id"))
    item_name: Mapped[str] = mapped_column(String(50))
    points_cost: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending 待领取 / fulfilled 已领取
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    user = relationship("User")
    item = relationship("RewardItem")
