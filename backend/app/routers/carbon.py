from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_teacher
from app.database import get_db
from app.models import CarbonActivity
from app.schemas import CarbonActivityCreate, CarbonActivityOut, StatsOut
from app.services import carbon_service

router = APIRouter(prefix="/api/activities", tags=["低碳行为"])


@router.post("", response_model=CarbonActivityOut, summary="提交一条低碳行为记录（登录用户本人）")
def create_activity(
    data: CarbonActivityCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return carbon_service.create_activity(db, data, user)


@router.get("", response_model=list[CarbonActivityOut], summary="查询低碳行为记录（学生只返回本人）")
def list_activities(
    role: str | None = Query(default=None, pattern="^(student|teacher)$"),
    username: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 学生强制只看自己的记录；教师可按角色 / 姓名筛选查看全部
    if user.role == "student":
        username = user.username
    return carbon_service.list_activities(db, role=role, username=username, limit=limit)


@router.get("/stats", response_model=StatsOut, summary="碳排放统计（教师）")
def get_stats(user=Depends(require_teacher), db: Session = Depends(get_db)):
    return carbon_service.get_stats(db)


@router.delete("/{activity_id}", summary="删除一条低碳行为记录（教师）")
def delete_activity(activity_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    activity = db.get(CarbonActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(activity)
    db.commit()
    return {"detail": "删除成功"}
