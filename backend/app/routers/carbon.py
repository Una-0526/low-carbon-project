from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CarbonActivity
from app.schemas import CarbonActivityCreate, CarbonActivityOut, StatsOut
from app.services import carbon_service

router = APIRouter(prefix="/api/activities", tags=["低碳行为"])


@router.post("", response_model=CarbonActivityOut, summary="提交一条低碳行为记录")
def create_activity(data: CarbonActivityCreate, db: Session = Depends(get_db)):
    return carbon_service.create_activity(db, data)


@router.get("", response_model=list[CarbonActivityOut], summary="查询低碳行为记录")
def list_activities(
    role: str | None = Query(default=None, pattern="^(student|teacher)$"),
    username: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return carbon_service.list_activities(db, role=role, username=username, limit=limit)


@router.get("/stats", response_model=StatsOut, summary="碳排放统计")
def get_stats(db: Session = Depends(get_db)):
    return carbon_service.get_stats(db)


@router.delete("/{activity_id}", summary="删除一条低碳行为记录")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.get(CarbonActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(activity)
    db.commit()
    return {"detail": "删除成功"}
