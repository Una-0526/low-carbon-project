"""碳核算 REST API：排放因子配置、建筑能耗记录、多维统计。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_teacher
from app.database import get_db
from app.models import CarbonFactor, EnergyRecord
from app.schemas import (
    CarbonFactorIn,
    CarbonFactorOut,
    CarbonStatsOut,
    EnergyRecordIn,
    EnergyRecordOut,
)
from app.services import carbon as carbon_service

router = APIRouter(prefix="/api/carbon", tags=["碳核算"])


@router.get("/factors", response_model=list[CarbonFactorOut], summary="查询全部排放因子")
def list_factors(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(CarbonFactor).order_by(CarbonFactor.id)))


@router.put("/factors/{factor_key}", response_model=CarbonFactorOut, summary="修改因子数值（教师）")
def update_factor(
    factor_key: str,
    data: CarbonFactorIn,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    factor = db.scalar(select(CarbonFactor).where(CarbonFactor.factor_key == factor_key))
    if factor is None:
        raise HTTPException(status_code=404, detail=f"因子不存在: {factor_key}")
    factor.factor = data.factor
    db.commit()
    db.refresh(factor)
    return factor


@router.post("/records", response_model=EnergyRecordOut, summary="录入建筑能耗记录（教师）")
def create_record(
    data: EnergyRecordIn,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    record, emissions = carbon_service.create_record(db, data)
    return EnergyRecordOut(**data.model_dump(), id=record.id, semester=record.semester,
                           emissions=emissions)


@router.get("/records", response_model=list[EnergyRecordOut], summary="查询能耗记录（含核算结果）")
def list_records(
    year: int | None = Query(default=None, ge=2000, le=2100),
    building: str | None = Query(default=None, max_length=50),
    semester: str | None = Query(default=None, max_length=20),
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    pairs = carbon_service.list_records(db, year=year, building=building, semester=semester)
    return [
        EnergyRecordOut(
            id=r.id, building=r.building, year=r.year, month=r.month, semester=r.semester,
            electricity_kwh=r.electricity_kwh, natural_gas_m3=r.natural_gas_m3,
            gasoline_l=r.gasoline_l, pv_kwh=r.pv_kwh, storage_kwh=r.storage_kwh,
            saving_kwh=r.saving_kwh, emissions=e,
        )
        for r, e in pairs
    ]


@router.delete("/records/{record_id}", summary="删除能耗记录（教师）")
def delete_record(record_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    record = db.get(EnergyRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"detail": "删除成功"}


@router.get("/stats", response_model=CarbonStatsOut, summary="碳排放统计（按建筑/月/学期）")
def get_stats(
    group_by: str = Query(pattern="^(building|month|semester)$"),
    year: int | None = Query(default=None, ge=2000, le=2100),
    building: str | None = Query(default=None, max_length=50),
    semester: str | None = Query(default=None, max_length=20),
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    rows = carbon_service.get_stats(db, group_by, year=year, building=building, semester=semester)
    return CarbonStatsOut(group_by=group_by, rows=rows)
