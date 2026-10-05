"""碳积分排行榜接口：学生 / 教师均可访问。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LeaderboardOut
from app.services import leaderboard as leaderboard_service

router = APIRouter(prefix="/api/leaderboard", tags=["积分排行榜"])

VALID_TYPES = {"personal", "dorm", "class"}
VALID_PERIODS = {"month", "year"}


@router.get("", response_model=LeaderboardOut)
def leaderboard(
    type: str = Query("personal", description="personal 个人榜 / dorm 宿舍榜 / class 班级榜"),
    period: str = Query("month", description="month 本月 / year 本年"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按维度与周期返回排行榜：items 全量列表 + me 当前学生定位。"""
    if type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的榜单类型：{type}")
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"无效的统计周期：{period}")
    return leaderboard_service.build(db, user, type, period)
