"""积分商城：默认商品种子数据与兑换逻辑。

兑换流程（单事务）：
1. 校验商品上架、积分足够；
2. 原子扣库存（stock > 0 条件更新，防止并发超卖）；
3. 写负数积分流水 + 兑换记录，统一 commit。
"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Redemption, RewardItem
from app.services import point_service

# 默认商品（reward_items 表为空时写入，参数可随时修改）
DEFAULT_REWARD_ITEMS: list[dict] = [
    {"name": "食堂优惠券", "category": "食堂", "points_cost": 50, "stock": 50,
     "description": "面值 5 元，全校食堂通用"},
    {"name": "超市折扣券", "category": "超市", "points_cost": 100, "stock": 20,
     "description": "校内超市 88 折，单次使用"},
    {"name": "文具兑换券", "category": "文具", "points_cost": 150, "stock": 10,
     "description": "笔记本 / 中性笔等文具自选一份"},
]


def ensure_default_reward_items(db: Session) -> None:
    """reward_items 表为空时写入默认商品。"""
    if db.scalar(select(RewardItem.id).limit(1)) is not None:
        return
    db.add_all([RewardItem(**item) for item in DEFAULT_REWARD_ITEMS])
    db.commit()


def redeem(db: Session, user_id: int, item: RewardItem) -> Redemption:
    """兑换商品：扣库存 → 扣积分（负流水）→ 生成兑换记录。调用方保证商品存在。"""
    result = db.execute(
        update(RewardItem)
        .where(RewardItem.id == item.id, RewardItem.stock > 0)
        .values(stock=RewardItem.stock - 1)
    )
    if result.rowcount == 0:
        raise ValueError("库存不足")
    point_service.credit(db, user_id, -item.points_cost, reason="redeem",
                         description=f"兑换：{item.name}")
    redemption = Redemption(
        user_id=user_id,
        item_id=item.id,
        item_name=item.name,
        points_cost=item.points_cost,
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return redemption
