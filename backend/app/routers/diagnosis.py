"""建筑异常诊断与节能方案库 REST API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_teacher
from app.database import get_db
from app.models import Solution
from app.schemas import BuildingDiagnosisOut, SolutionIn, SolutionOut
from app.services import carbon as carbon_service
from app.services import diagnosis as diagnosis_service

router = APIRouter(prefix="/api/diagnosis", tags=["异常诊断"])


def _solution_out(solution: Solution, db: Session) -> SolutionOut:
    grid_factor = carbon_service.load_factors(db).get("grid_electricity", 0.0)
    return SolutionOut(**solution.__dict__, **diagnosis_service.compute_solution(solution, grid_factor))


@router.get("/buildings", response_model=list[BuildingDiagnosisOut], summary="建筑异常诊断（本月环比 + 夜间用电占比）")
def diagnose_buildings(user=Depends(require_teacher), db: Session = Depends(get_db)):
    """判定规则：本月碳排放环比上月 > 15% 且夜间(22:00-6:00)用电占比 > 40% → 异常。"""
    return diagnosis_service.diagnose_buildings(db)


@router.get("/solutions", response_model=list[SolutionOut], summary="方案库列表（含测算结果）")
def list_solutions(user=Depends(require_teacher), db: Session = Depends(get_db)):
    solutions = db.scalars(select(Solution).order_by(Solution.id)).all()
    return [_solution_out(s, db) for s in solutions]


@router.post("/solutions", response_model=SolutionOut, status_code=201, summary="新增方案（教师）")
def create_solution(data: SolutionIn, user=Depends(require_teacher), db: Session = Depends(get_db)):
    if db.scalar(select(Solution.id).where(Solution.name == data.name)):
        raise HTTPException(status_code=400, detail=f"方案名已存在: {data.name}")
    solution = Solution(**data.model_dump())
    db.add(solution)
    db.commit()
    db.refresh(solution)
    return _solution_out(solution, db)


@router.put("/solutions/{solution_id}", response_model=SolutionOut, summary="修改方案参数（教师）")
def update_solution(
    solution_id: int,
    data: SolutionIn,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    solution = db.get(Solution, solution_id)
    if solution is None:
        raise HTTPException(status_code=404, detail=f"方案不存在: {solution_id}")
    dup = db.scalar(select(Solution.id).where(Solution.name == data.name, Solution.id != solution_id))
    if dup:
        raise HTTPException(status_code=400, detail=f"方案名已存在: {data.name}")
    for key, value in data.model_dump().items():
        setattr(solution, key, value)
    db.commit()
    db.refresh(solution)
    return _solution_out(solution, db)


@router.delete("/solutions/{solution_id}", summary="删除方案（教师）")
def delete_solution(solution_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    solution = db.get(Solution, solution_id)
    if solution is None:
        raise HTTPException(status_code=404, detail=f"方案不存在: {solution_id}")
    db.delete(solution)
    db.commit()
    return {"deleted": solution_id}
