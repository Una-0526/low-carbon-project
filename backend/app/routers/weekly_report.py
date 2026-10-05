"""我的碳周报接口（学生端）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import WeekCardOut, WeeklyReportOut
from app.services import weekly_report as weekly_report_service

router = APIRouter(prefix="/api/weekly-report", tags=["碳周报"])


@router.get("/current", response_model=WeekCardOut)
def current_week(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """本周碳周报卡片（实时计算，不落库）。"""
    return weekly_report_service.compute_week_card(db, user)


@router.get("/history", response_model=list[WeeklyReportOut])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """历史周报列表；缺失的已完成周在此自动补生成（等效每周一自动生成）。"""
    return weekly_report_service.list_history(db, user)
