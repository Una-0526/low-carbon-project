"""碳积分商城接口。

学生：上架商品列表、积分兑换、我的兑换记录。
教师：商品管理（新增 / 编辑 / 上下架 / 调整积分库存）、兑换记录发放。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_teacher
from app.database import get_db
from app.models import Redemption, RewardItem, User
from app.schemas import (RedeemResultOut, RedemptionOut, RewardItemIn,
                         RewardItemOut)
from app.services import mall as mall_service
from app.services import point_service

router = APIRouter(prefix="/api/mall", tags=["积分商城"])
admin_router = APIRouter(prefix="/api/mall/admin", tags=["积分商城（教师）"])


def _redemption_out(redemption: Redemption) -> RedemptionOut:
    return RedemptionOut(
        id=redemption.id,
        user_id=redemption.user_id,
        username=redemption.user.username,
        item_id=redemption.item_id,
        item_name=redemption.item_name,
        points_cost=redemption.points_cost,
        status=redemption.status,
        created_at=redemption.created_at,
        fulfilled_at=redemption.fulfilled_at,
    )


# ---------- 学生端 ----------

@router.get("/items", response_model=list[RewardItemOut])
def list_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """上架商品列表（按所需积分升序）。"""
    rows = db.scalars(
        select(RewardItem)
        .where(RewardItem.is_active.is_(True))
        .order_by(RewardItem.points_cost.asc(), RewardItem.id.asc())
    ).all()
    return list(rows)


@router.post("/items/{item_id}/redeem", response_model=RedeemResultOut)
def redeem_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """积分兑换：扣减积分、扣库存并生成兑换记录（待领取）。"""
    item = db.get(RewardItem, item_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    if point_service.total(db, user.id) < item.points_cost:
        raise HTTPException(status_code=400, detail="碳积分不足，无法兑换")
    try:
        redemption = mall_service.redeem(db, user.id, item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    remaining = point_service.total(db, user.id)
    return RedeemResultOut(redemption=_redemption_out(redemption), remaining_points=remaining)


@router.get("/redemptions/me", response_model=list[RedemptionOut])
def my_redemptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的兑换记录（新→旧）。"""
    rows = db.scalars(
        select(Redemption)
        .where(Redemption.user_id == user.id)
        .order_by(Redemption.created_at.desc(), Redemption.id.desc())
    ).all()
    return [_redemption_out(r) for r in rows]


# ---------- 教师端 ----------

@admin_router.get("/items", response_model=list[RewardItemOut])
def admin_list_items(user: User = Depends(require_teacher), db: Session = Depends(get_db)):
    """全部商品（含已下架）。"""
    rows = db.scalars(select(RewardItem).order_by(RewardItem.id.asc())).all()
    return list(rows)


@admin_router.post("/items", response_model=RewardItemOut, status_code=201)
def admin_create_item(
    data: RewardItemIn,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """新增商品。"""
    if db.scalar(select(RewardItem).where(RewardItem.name == data.name)):
        raise HTTPException(status_code=400, detail="同名商品已存在")
    item = RewardItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@admin_router.put("/items/{item_id}", response_model=RewardItemOut)
def admin_update_item(
    item_id: int,
    data: RewardItemIn,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """编辑商品：名称 / 分类 / 所需积分 / 库存 / 上下架。"""
    item = db.get(RewardItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    dup = db.scalar(select(RewardItem).where(RewardItem.name == data.name, RewardItem.id != item_id))
    if dup:
        raise HTTPException(status_code=400, detail="同名商品已存在")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@admin_router.get("/redemptions", response_model=list[RedemptionOut])
def admin_list_redemptions(
    status: str | None = None,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """全部兑换记录（新→旧），可按状态筛选。"""
    query = select(Redemption)
    if status:
        query = query.where(Redemption.status == status)
    rows = db.scalars(query.order_by(Redemption.created_at.desc(), Redemption.id.desc())).all()
    return [_redemption_out(r) for r in rows]


@admin_router.post("/redemptions/{redemption_id}/fulfill", response_model=RedemptionOut)
def admin_fulfill_redemption(
    redemption_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """标记兑换记录为已领取（线下发放凭证后操作）。"""
    redemption = db.get(Redemption, redemption_id)
    if redemption is None:
        raise HTTPException(status_code=404, detail="兑换记录不存在")
    if redemption.status == "fulfilled":
        raise HTTPException(status_code=400, detail="该记录已领取")
    redemption.status = "fulfilled"
    redemption.fulfilled_at = datetime.now()
    db.commit()
    db.refresh(redemption)
    return _redemption_out(redemption)
