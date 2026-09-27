"""碳中和路径模拟 REST API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_teacher
from app.database import get_db
from app.services import pathway as pathway_service

router = APIRouter(prefix="/api/pathway", tags=["碳中和路径"])


@router.get("/simulate", summary="三情景碳中和路径模拟（教师）")
def simulate(user=Depends(require_teacher), db: Session = Depends(get_db)):
    """基准排放取最近 12 个月碳排放合计；三情景按年减排率线性推演至 2060。"""
    result = pathway_service.simulate(db)
    if not result["scenarios"]:
        raise HTTPException(status_code=400, detail=result["note"])
    return result
