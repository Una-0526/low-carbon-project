"""绿色打卡与积分流水接口。

学生：任务列表、提交打卡（multipart，可带定位与照片）、我的打卡、我的积分流水。
教师：查看全部打卡（可筛选）、通过/驳回、查看任意学生积分流水。
"""

import json
import uuid
from pathlib import Path

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_teacher
from app.database import get_db
from app.models import Checkin, User
from app.schemas import (ApproveResultOut, CheckinOut, CheckinSummaryOut,
                         MyDiagnosisOut, PointSummaryOut, PointTransactionOut,
                         RejectIn)
from app.services import checkin_service, point_service

router = APIRouter(prefix="/api/checkins", tags=["绿色打卡"])
points_router = APIRouter(prefix="/api/points", tags=["积分流水"])

# backend/uploads（checkin.py 位于 app/routers/ 下，向上三级到 backend/）
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5MB


def _to_out(checkin: Checkin) -> CheckinOut:
    return CheckinOut(
        id=checkin.id,
        user_id=checkin.user_id,
        username=checkin.user.username,
        task_type=checkin.task_type,
        photo_path=checkin.photo_path,
        latitude=checkin.latitude,
        longitude=checkin.longitude,
        status=checkin.status,
        ai_flagged=checkin.ai_flagged,
        ai_flags=json.loads(checkin.ai_flags) if checkin.ai_flags else [],
        points_awarded=checkin.points_awarded,
        review_reason=checkin.review_reason,
        note=checkin.note,
        created_at=checkin.created_at,
    )


def _get_checkin(db: Session, checkin_id: int) -> Checkin:
    checkin = db.get(Checkin, checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")
    return checkin


def _save_photo(photo: UploadFile) -> str:
    """校验并保存上传照片，返回可访问的相对 URL。"""
    ext = ALLOWED_IMAGE_TYPES.get(photo.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="照片仅支持 jpg/png/webp")
    data = photo.file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="照片不能超过 5MB")
    UPLOAD_DIR.mkdir(exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / name).write_bytes(data)
    return f"/uploads/{name}"


# ---------- 学生端 ----------

@router.get("/tasks")
def list_tasks(user: User = Depends(get_current_user)):
    """任务类型与基础积分。"""
    return [{"task_type": k, "points": v} for k, v in checkin_service.TASK_POINTS.items()]


@router.post("", response_model=CheckinOut, status_code=201)
async def create_checkin(
    task_type: str = Form(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    note: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交打卡：可带定位坐标、备注与照片。服务端自动执行 AI 防作弊检查并打标。"""
    if task_type not in checkin_service.TASK_POINTS:
        raise HTTPException(status_code=400, detail=f"无效任务类型，可选：{'/'.join(checkin_service.TASK_POINTS)}")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="定位需同时提供经纬度")
    if note and len(note) > 200:
        raise HTTPException(status_code=400, detail="备注不能超过 200 字")
    photo_path = _save_photo(photo) if photo else None
    checkin, _flags = checkin_service.create_checkin(
        db, user, task_type, latitude, longitude, photo_path, note=note
    )
    return _to_out(checkin)


@router.get("/me", response_model=list[CheckinOut])
def my_checkins(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的打卡记录（新→旧）。"""
    rows = db.scalars(
        select(Checkin).where(Checkin.user_id == user.id).order_by(Checkin.created_at.desc(), Checkin.id.desc())
    ).all()
    return [_to_out(c) for c in rows]


@router.get("/me/summary", response_model=CheckinSummaryOut)
def my_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的积分与连续打卡天数。"""
    return checkin_service.student_summary(db, user.id)


@router.get("/me/diagnosis", response_model=MyDiagnosisOut)
def my_diagnosis(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的碳诊断：本周/本月减碳、行为分类统计、个性化建议、月度班级排名百分位。"""
    return checkin_service.my_diagnosis(db, user)


# ---------- 教师端 ----------

@router.get("", response_model=list[CheckinOut])
def list_all_checkins(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    ai_flagged: bool | None = Query(default=None),
    user_id: int | None = Query(default=None),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """全部打卡记录，可按状态/AI标记/学生筛选（新→旧）。"""
    query = select(Checkin)
    if status:
        query = query.where(Checkin.status == status)
    if ai_flagged is not None:
        query = query.where(Checkin.ai_flagged == ai_flagged)
    if user_id is not None:
        query = query.where(Checkin.user_id == user_id)
    rows = db.scalars(query.order_by(Checkin.created_at.desc(), Checkin.id.desc())).all()
    return [_to_out(c) for c in rows]


@router.post("/{checkin_id}/approve", response_model=ApproveResultOut)
def approve_checkin(
    checkin_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """审核通过：积分入账 point_transactions，命中里程碑加发连续奖励。"""
    result = checkin_service.approve_checkin(db, _get_checkin(db, checkin_id))
    checkin = _get_checkin(db, checkin_id)
    return ApproveResultOut(checkin=_to_out(checkin), streak=result["streak"], bonus=result["bonus"])


@router.post("/{checkin_id}/reject", response_model=CheckinOut)
def reject_checkin(
    checkin_id: int,
    data: RejectIn,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """审核驳回：不发积分，可记录原因。"""
    return _to_out(checkin_service.reject_checkin(db, _get_checkin(db, checkin_id), data.reason))


# ---------- 积分流水 ----------

@points_router.get("/me", response_model=PointSummaryOut)
def my_points(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的积分流水与累计积分。"""
    return PointSummaryOut(
        total_points=point_service.total(db, user.id),
        transactions=[PointTransactionOut.model_validate(t) for t in point_service.list_transactions(db, user.id)],
    )


@points_router.get("/transactions", response_model=PointSummaryOut)
def user_points(
    user_id: int = Query(...),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """教师查看指定学生的积分流水。"""
    return PointSummaryOut(
        total_points=point_service.total(db, user_id),
        transactions=[PointTransactionOut.model_validate(t) for t in point_service.list_transactions(db, user_id)],
    )
